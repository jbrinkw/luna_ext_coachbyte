# CoachByte – Technical Guide

CoachByte is Luna’s strength-training copilot: agents can program workouts, auto-complete sets, and monitor PRs while a React UI gives humans the same control surface. Everything is backed by a shared PostgreSQL database so the UI, automation tools, and backend service always see the same state.

```
┌─────────┐         tool calls           ┌──────────────┐        REST         ┌────────────┐
│  Luna   │ ───────────────────────────▶ │ Python tools │ ────────────────┐   │  Express   │
│ agents  │                              │ coachbyte…py │                 │   │ backend    │
└─────────┘                              └──────────────┘                 │   └────────────┘
         ▲                                         ▲                      │         │
         │                                         │ shared tables        │         │pg Pool
         │                                         │ (workout data)       ▼         ▼
         │                     browser             │             ┌────────────────────┐
         └───────── React UI (Vite dev server) ◀───┴──────────── │   PostgreSQL DB    │
                                                                └────────────────────┘
```

## Directory map

| Area | Path | Notes |
| --- | --- | --- |
| Agent tools | `extensions/coachbyte/tools/coachbyte_tools.py` | Pydantic + psycopg2 tool implementations wired into MCP via `tool_config.json`. |
| Backend service | `extensions/coachbyte/services/backend/` | Node 18+ Express server (`server.js`) + data access (`db.js`). |
| UI | `extensions/coachbyte/ui/` | React + Vite SPA (polls backend every 5 s). |
| Config | `extensions/coachbyte/config.json` | Declares required secrets and service metadata for Luna. |
| Python deps | `extensions/coachbyte/requirements.txt` | Install inside the Luna Python environment. |

## Environment requirements

CoachByte persists everything in PostgreSQL. Define the following variables in the repository-level `.env` that Luna sources:

```
DB_HOST=…
DB_PORT=5432
DB_NAME=…
DB_USER=…
DB_PASSWORD=…
# optional:
DB_SCHEMA=coachbyte   # schema search_path if you isolate CoachByte tables
```

The backend creates/updates tables on boot, so no manual migrations are required. The Python tools load the same `.env` and will fail fast if any variable is missing.

## Installing dependencies

```bash
# Python tooling (agent-side)
pip install -r extensions/coachbyte/requirements.txt

# Backend service
cd extensions/coachbyte/services/backend
pnpm install   # or npm install

# UI
cd extensions/coachbyte/ui
npm install
```

## Running the services locally

1. **Database** – Provide a reachable PostgreSQL instance and ensure the configured user can create tables.
2. **Backend** – `cd extensions/coachbyte/services/backend && PORT=5300 node server.js`
   * Luna’s supervisor normally calls `start.sh` and injects the port; health check is `GET /api/days`.
3. **UI** – `cd extensions/coachbyte/ui && PORT=5200 npm run dev`
   * Requests to `/api/coachbyte/*` are proxied to the backend by Luna’s Caddy setup; when running outside Luna, change `API_BASE` in `src/api.js` or start Vite with a proxy (e.g., `npm run dev -- --host --port 5200 --proxy /api/coachbyte=http://localhost:5300`).
4. **Agent tools** – Loaded automatically by Luna once the Python requirements and secrets are in place.

## Data model (PostgreSQL)

| Table | Purpose |
| --- | --- |
| `exercises` | Canonical exercise names. Helper `getExerciseId` upserts on demand. |
| `daily_logs` | One row per training day (EST date, UUID primary key, optional summary). |
| `planned_sets` | Queue of sets for a day. Supports `relative` flag for percentage-based loads and stores order/rest metadata. |
| `completed_sets` | Logged work sets with timestamps; joined with `planned_sets` to move through the queue. |
| `split_sets` | Weekly split templates (0–6 for Sunday–Saturday) that auto-populate a day if no custom plan exists. |
| `split_notes` | Single-row freeform notes for weekly programming context. |
| `tracked_exercises` / `tracked_prs` | Control which movements have PR cards and store manually curated PR targets. |
| `timer` | Single-row countdown timer. Completing a planned set seeds the rest timer for the following set. |

`db.js` ensures all of the above exist on startup, adds missing columns (`relative`, timestamptz conversions), seeds default tracked exercises, and can optionally populate sample data via `populateSample`.

## Backend API surface (`server.js`)

The Express app (default `127.0.0.1:5300`) exposes JSON endpoints consumed by both the UI and the tools:

### Days & plans

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/days` | List all `daily_logs` (ensures “today” exists first). |
| `POST` | `/api/days` | Create a specific date. Payload `{date: "YYYY-MM-DD"}`. |
| `DELETE` | `/api/days/:id` | Remove a day (cascades to plan/completed sets). |
| `GET` | `/api/days/:id` | Returns `{log, plan, completed}` with relative loads resolved against current PRs. |
| `POST` | `/api/days/:id/plan` | Add a planned set to a day. |
| `PUT` | `/api/plan/:id` | Update set metadata. |
| `DELETE` | `/api/plan/:id` | Delete a planned set. |
| `POST` | `/api/days/:id/completed` | Log a completed set, set the global rest timer to the upcoming set’s `rest`, and echo the stored row. |
| `PUT` | `/api/completed/:id` / `DELETE` same | Edit / remove logged sets. |
| `PUT` | `/api/days/:id/summary` | Update the textual summary. |

### Weekly split & notes

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/split` or `/api/split/:day` | Fetch the template split (all days or single day index). |
| `POST` | `/api/split/:day` | Insert a template set. |
| `PUT` | `/api/split/plan/:id` | Update a template set. |
| `DELETE` | `/api/split/plan/:id` | Remove a template set. |
| `GET` | `/api/split/notes` / `PUT` same | Read or replace the global split notes blob. |

`ensureTodayPlan` (called before almost every handler) guarantees the current EST day exists and, if blank, clones that weekday’s `split_sets` into `planned_sets`.

### Tracking, PRs, timer

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/prs` | Returns best loads per reps for tracked exercises based on real completions. |
| `GET/PUT/DELETE` | `/api/tracked-prs` | Manage the curated PR targets table. |
| `GET/POST/DELETE` | `/api/tracked-exercises` | Control which exercises appear in PR widgets. |
| `GET` | `/api/timer` | Read the countdown status (running/expired/no_timer, remaining seconds, ISO end time). |

The timer endpoints are read-only because the countdown is primarily controlled by `POST /api/days/:id/completed` and the Python tool `COACHBYTE_ACTION_set_timer`. If the DB is unavailable, both the UI and tools fall back to the file-based helper `ui/tools/timer_temp.py`.

## Agent tool surface (`coachbyte_tools.py`)

All tools share `_get_connection()` and Pydantic request models. Each function returns `(success: bool, payload: str)` to Luna’s MCP router:

| Tool | Purpose |
| --- | --- |
| `COACHBYTE_UPDATE_new_daily_plan` | Append or prepend sets to today’s plan (uses `order` field to position items). |
| `COACHBYTE_GET_today_plan` | Echo today’s plan queue. |
| `COACHBYTE_ACTION_complete_next_set` | Dequeues the next planned set (optionally filtered by exercise and rep/load overrides) and logs it in `completed_sets`. |
| `COACHBYTE_ACTION_log_completed_set` | Log ad-hoc work that is not part of the queue. |
| `COACHBYTE_UPDATE_summary` | Replace today’s written summary. |
| `COACHBYTE_GET_recent_history` | Return the past _N_ days (includes planned + completed sets). |
| `COACHBYTE_UPDATE_weekly_split_day` | Replace the template for a named weekday (Sunday–Saturday). |
| `COACHBYTE_GET_weekly_split` | Fetch full split or a single day’s template. |
| `COACHBYTE_ACTION_set_timer` / `COACHBYTE_GET_timer` | Manage the global rest timer. |

Because these functions connect straight to PostgreSQL with psycopg2, they bypass the HTTP layer and can act even if the Node service is down, provided the database is reachable.

## React UI (`extensions/coachbyte/ui/src`)

Key components:

* `App.jsx` – Loads / polls `/api/days`, renders the day list, and toggles between views (Day detail, PR tracker, split planner/editor). Poll interval is 5 s so completions recorded elsewhere show up quickly.
* `DayDetail.jsx` – Displays today’s queue (`plan`) with calculated vs original load, rest timer state, and completion history. Supports CRUD operations through the API routes above.
* `SplitPlanner.jsx` / `EditSplitPage.jsx` – Visualize the 7-day split, edit template sets, and manage split notes.
* `PRTracker.jsx` – Displays actual PRs from `GET /api/prs` and targeted PRs from `tracked_prs`.
* `ChatBar.jsx` / `ChatSidebar.jsx` – Shortcut buttons and status cards optimized for use alongside Luna chat sessions.

All fetch helpers use `API_BASE = '/api/coachbyte'`, which Luna’s Caddy reverse proxy maps to the backend container.

## How the system behaves

1. **Day bootstrap** – Every API handler first calls `ensureTodayPlan()`, which:
   * Creates today’s `daily_logs` entry (EST) if it doesn’t exist.
   * Copies template sets from `split_sets` into `planned_sets` when the day is empty.
2. **Relative loads** – `split_sets` can store percentage-of-1RM loads. `db.getDay` converts them to concrete weights using the latest measured PRs (Epley estimate for reps > 1) and returns both `calculatedLoad` and the original percentage so the UI can render both.
3. **Completing sets** – When `/completed` is hit (via UI or tool), the backend:
   * Writes the completed row and removes the set from the queue when `planned_set_id` is present.
   * Looks at the next queued set and sets the timer (`timer` table) to its `rest` duration so the UI and tools can display the countdown.
4. **Timers during outages** – If the database is offline, the lightweight `timer_temp.py` file storage keeps timers working so workouts can continue; the UI exposes the same helper.
5. **PR aggregation** – `getPRs` groups `completed_sets` by exercise/reps for the tracked exercise list, while `tracked_prs` lets athletes set targets (e.g., “Bench 1×275”). The UI juxtaposes actual vs target.

## Development & troubleshooting

* **Seeding data** – Temporarily change `db.initDb(false)` to `db.initDb(true)` in `server.js` to populate the sample split + historical logs, then revert.
* **Schema updates** – Add columns in `db.js` inside the `DO $$` migration blocks so they run idempotently on every boot.
* **Connection issues** – Both backend and tools log the resolved DB config (minus password). Confirm `.env` is loaded from the repo root, especially when running scripts directly.
* **Caddy routing** – The UI comments remind you that `/api/coachbyte` is the ingress path. When deploying outside Luna, configure your reverse proxy or adjust `API_BASE`.

With the above setup, CoachByte delivers synchronized workout automation across Luna agents, the web UI, and the REST backend, all powered by a single source of truth in PostgreSQL.
