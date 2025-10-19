"""CoachByte workout tracking and planning tools for Luna.

This module provides tools for planning workouts, tracking progress, managing
weekly splits, and setting rest timers.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, timedelta, datetime, timezone
from pydantic import BaseModel, Field
import os
import json
import subprocess
import uuid

import psycopg2
import psycopg2.extras

# Load .env from repo root (two levels up from this file)
try:
    from dotenv import load_dotenv
    _repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _env_path = os.path.join(_repo_root, ".env")
    load_dotenv(_env_path)
except Exception:
    pass


# Constants
MAX_LOAD = 2000
MAX_REPS = 100

DAY_MAP = {
    "sunday": 0,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
}

SYSTEM_PROMPT = """The user has access to workout planning and tracking tools.

You can help them create daily workout plans, complete sets from their plan,
log extra sets, update workout summaries, view recent history, manage weekly
split schedules, and set/check rest timers.

Tools validate reps (1-100) and load (0-2000). Prefer using complete_next_set
to advance through the planned workout queue."""


# Helper functions
def _get_connection():
    """Get database connection from environment variables."""
    url = os.getenv("DATABASE_URL")
    if isinstance(url, str) and url.strip():
        return psycopg2.connect(url)
    
    # Fallback to individual connection parameters
    host = os.getenv("PGHOST") or os.getenv("DB_HOST")
    port_str = os.getenv("PGPORT") or os.getenv("DB_PORT")
    dbname = os.getenv("PGDATABASE") or os.getenv("DB_NAME")
    user = os.getenv("PGUSER") or os.getenv("DB_USER")
    password = os.getenv("PGPASSWORD") or os.getenv("DB_PASSWORD")
    
    if not all([host, dbname, user, password]):
        raise RuntimeError("Database configuration missing. Set DATABASE_URL environment variable.")
    
    conn = psycopg2.connect(
        host=host,
        port=int(port_str) if isinstance(port_str, str) and port_str.strip() else 5432,
        dbname=dbname,
        user=user,
        password=password,
    )
    
    # Optional: set search_path if DB_SCHEMA is provided
    schema = os.getenv("DB_SCHEMA")
    if isinstance(schema, str) and schema.strip():
        try:
            safe = schema.strip().replace(";", "")
            cur = conn.cursor()
            cur.execute(f"SET search_path TO {safe}")
            cur.close()
        except Exception:
            pass
    
    return conn


def _get_exercise_id(conn, name: str) -> int:
    """Get or create exercise ID by name."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM exercises WHERE name = %s", (name,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute("INSERT INTO exercises (name) VALUES (%s) RETURNING id", (name,))
    return cur.fetchone()["id"]


def _get_today_log_id(conn):
    """Get or create today's daily log ID."""
    today = date.today().isoformat()
    cur = conn.cursor()
    cur.execute("SELECT id FROM daily_logs WHERE log_date = %s", (today,))
    row = cur.fetchone()
    if row:
        return row[0]
    
    log_id = str(uuid.uuid4())
    cur.execute("INSERT INTO daily_logs (id, log_date) VALUES (%s, %s)", (log_id, today))
    conn.commit()
    return log_id


# Pydantic argument models
class PlanSetItem(BaseModel):
    exercise: str = Field(..., description="Exercise name")
    reps: int = Field(..., ge=1, le=MAX_REPS, description="Number of reps")
    load: float = Field(..., ge=0, le=MAX_LOAD, description="Weight/load")
    rest: int = Field(60, ge=0, le=600, description="Rest time in seconds")
    order: int = Field(0, description="Order in plan (0=append, -1=prepend)")


class COACHBYTE_UPDATE_NewDailyPlanArgs(BaseModel):
    items: List[PlanSetItem] = Field(..., description="List of planned sets")


class COACHBYTE_ACTION_CompleteNextSetArgs(BaseModel):
    exercise: Optional[str] = Field(None, description="Specific exercise to complete")
    reps: Optional[int] = Field(None, ge=1, le=MAX_REPS, description="Override reps")
    load: Optional[float] = Field(None, ge=0, le=MAX_LOAD, description="Override load")


class COACHBYTE_ACTION_LogCompletedSetArgs(BaseModel):
    exercise: str = Field(..., description="Exercise name")
    reps: int = Field(..., ge=1, le=MAX_REPS, description="Reps completed")
    load: float = Field(..., ge=0, le=MAX_LOAD, description="Load used")


class COACHBYTE_UPDATE_SummaryArgs(BaseModel):
    text: str = Field(..., description="Summary text for today's workout")


class COACHBYTE_GET_RecentHistoryArgs(BaseModel):
    days: int = Field(..., ge=1, le=365, description="Number of days to retrieve")


class SplitSetItem(BaseModel):
    exercise: str = Field(..., description="Exercise name")
    reps: int = Field(..., ge=1, le=MAX_REPS, description="Number of reps")
    load: float = Field(..., ge=0, le=MAX_LOAD, description="Weight/load or percentage")
    rest: int = Field(60, ge=0, le=600, description="Rest time in seconds")
    order: int = Field(1, description="Order in split")
    relative: bool = Field(False, description="If true, load is % of 1RM")


class COACHBYTE_UPDATE_WeeklySplitDayArgs(BaseModel):
    day: str = Field(..., description="Day name (monday, tuesday, etc)")
    items: List[SplitSetItem] = Field(..., description="List of sets for this day")


class COACHBYTE_GET_WeeklySplitArgs(BaseModel):
    day: Optional[str] = Field(None, description="Specific day (or None for all)")


class COACHBYTE_ACTION_SetTimerArgs(BaseModel):
    minutes: int = Field(..., ge=1, le=180, description="Timer duration in minutes")


# Tool functions
def COACHBYTE_UPDATE_new_daily_plan(items: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Create today's daily workout plan with a list of planned sets.
    Example Prompt: Make a plan for today: bench press 10x135 at order 1; squat 8x185 at order 2.
    Example Response: {"success": true, "message": "planned 2 sets for today"}
    Example Args: {"items": [{"exercise": "bench press", "reps": 10, "load": 135, "rest": 60, "order": 1}]}
    """
    try:
        args = COACHBYTE_UPDATE_NewDailyPlanArgs(items=items)
        conn = _get_connection()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            log_id = _get_today_log_id(conn)
            
            cur.execute(
                "SELECT MIN(order_num) as min_order, MAX(order_num) as max_order FROM planned_sets WHERE log_id = %s",
                (log_id,),
            )
            result = cur.fetchone() or {}
            min_order = result.get("min_order") if result.get("min_order") is not None else 0
            max_order = result.get("max_order") if result.get("max_order") is not None else 0
            
            details: List[str] = []
            for item in args.items:
                exercise_id = _get_exercise_id(conn, item.exercise)
                
                if item.order == 0:
                    order_num = max_order + 1
                    max_order = order_num
                elif item.order == -1:
                    order_num = min_order - 1
                    min_order = order_num
                else:
                    order_num = item.order
                
                cur.execute(
                    "INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load, rest) VALUES (%s, %s, %s, %s, %s, %s)",
                    (log_id, exercise_id, order_num, item.reps, item.load, item.rest),
                )
                details.append(f"{item.exercise}, {item.reps} reps at {item.load:g} pounds as set {order_num}")
            
            conn.commit()
            
            summary = f"planned {len(args.items)} sets for today"
            if details:
                summary += ": " + "; ".join(details)
            
            return (True, json.dumps({"success": True, "message": summary}))
        finally:
            conn.close()
    except Exception as e:
        return (False, f"Error creating plan: {str(e)}")


def COACHBYTE_GET_today_plan() -> Tuple[bool, str]:
    """Return today's planned workout sets in order.
    Example Prompt: What's my workout plan for today?
    Example Response: {"success": true, "plan": [{"exercise": "bench press", "reps": 10, "load": 135}]}
    Example Args: {}
    """
    try:
        conn = _get_connection()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            log_id = _get_today_log_id(conn)
            cur.execute(
                """
                SELECT e.name as exercise, reps, load, rest, order_num
                FROM planned_sets ps
                JOIN exercises e ON ps.exercise_id = e.id
                WHERE log_id = %s
                ORDER BY order_num
                """,
                (log_id,),
            )
            rows = [dict(row) for row in cur.fetchall()]
            return (True, json.dumps({"success": True, "plan": rows}))
        finally:
            conn.close()
    except Exception as e:
        return (False, f"Error getting plan: {str(e)}")


def COACHBYTE_ACTION_complete_next_set(exercise: Optional[str] = None, reps: Optional[int] = None, load: Optional[float] = None) -> Tuple[bool, str]:
    """Complete the next planned set (optionally specify exercise and/or override reps/load).
    Example Prompt: Complete my next set; if it's squats, do 8 reps instead.
    Example Response: {"success": true, "message": "Completed squats: 8 reps @ 185 load"}
    Example Args: {"exercise": "squats", "reps": 8, "load": 185}
    """
    try:
        args = COACHBYTE_ACTION_CompleteNextSetArgs(exercise=exercise, reps=reps, load=load)
        conn = _get_connection()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            log_id = _get_today_log_id(conn)
            
            if args.exercise:
                cur.execute(
                    """
                    SELECT ps.id, ps.exercise_id, e.name as exercise, ps.reps, ps.load, ps.rest, ps.order_num
                    FROM planned_sets ps
                    JOIN exercises e ON ps.exercise_id = e.id
                    WHERE ps.log_id = %s AND e.name = %s
                    ORDER BY ps.order_num
                    LIMIT 1
                    """,
                    (log_id, args.exercise),
                )
            else:
                cur.execute(
                    """
                    SELECT ps.id, ps.exercise_id, e.name as exercise, ps.reps, ps.load, ps.rest, ps.order_num
                    FROM planned_sets ps
                    JOIN exercises e ON ps.exercise_id = e.id
                    WHERE ps.log_id = %s
                    ORDER BY ps.order_num
                    LIMIT 1
                    """,
                    (log_id,),
                )
            
            planned_set = cur.fetchone()
            if not planned_set:
                msg = f"No planned sets found for exercise: {args.exercise}" if args.exercise else "No planned sets remaining for today"
                return (False, json.dumps({"success": False, "message": msg}))
            
            actual_reps = args.reps if args.reps is not None else planned_set["reps"]
            actual_load = args.load if args.load is not None else planned_set["load"]
            
            cur.execute(
                "INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done, completed_at) VALUES (%s, %s, %s, %s, %s)",
                (log_id, planned_set["exercise_id"], actual_reps, actual_load, datetime.now(timezone.utc)),
            )
            cur.execute("DELETE FROM planned_sets WHERE id = %s", (planned_set["id"],))
            conn.commit()
            
            rest_time = planned_set.get("rest", 60) or 60
            rest_info = ""
            if rest_time > 0:
                try:
                    # Timer script is in ui/tools relative to extension root
                    ext_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    timer_script = os.path.join(ext_root, "ui", "tools", "timer_temp.py")
                    if os.path.exists(timer_script):
                        result = subprocess.run(
                            ["python", timer_script, "set", str(rest_time), "seconds"],
                            capture_output=True,
                            text=True,
                            cwd=os.path.dirname(timer_script)
                        )
                        if result.returncode == 0:
                            rest_info = f" Rest timer set for {rest_time} seconds."
                except Exception:
                    pass
            
            result_msg = f"Completed {planned_set['exercise']}: {actual_reps} reps @ {actual_load} load"
            if args.reps is not None or args.load is not None:
                result_msg += f" (planned: {planned_set['reps']} reps @ {planned_set['load']} load)"
            result_msg += rest_info
            
            return (True, json.dumps({"success": True, "message": result_msg}))
        finally:
            conn.close()
    except Exception as e:
        return (False, f"Error completing set: {str(e)}")


def COACHBYTE_ACTION_log_completed_set(exercise: str, reps: int, load: float) -> Tuple[bool, str]:
    """Log an unplanned, completed set (not from the queue).
    Example Prompt: I did extra push-ups: 20 reps at bodyweight.
    Example Response: {"success": true, "message": "logged: push-ups, 20 reps @ 0"}
    Example Args: {"exercise": "push-ups", "reps": 20, "load": 0}
    """
    try:
        args = COACHBYTE_ACTION_LogCompletedSetArgs(exercise=exercise, reps=reps, load=load)
        conn = _get_connection()
        try:
            cur = conn.cursor()
            log_id = _get_today_log_id(conn)
            exercise_id = _get_exercise_id(conn, args.exercise)
            cur.execute(
                "INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done, completed_at) VALUES (%s, %s, %s, %s, %s)",
                (log_id, exercise_id, args.reps, args.load, datetime.now(timezone.utc)),
            )
            conn.commit()
            
            msg = f"logged: {args.exercise}, {args.reps} reps @ {args.load:g}"
            return (True, json.dumps({"success": True, "message": msg}))
        finally:
            conn.close()
    except Exception as e:
        return (False, f"Error logging set: {str(e)}")


def COACHBYTE_UPDATE_summary(text: str) -> Tuple[bool, str]:
    """Update today's workout summary text.
    Example Prompt: Add summary: Great session, felt strong on bench.
    Example Response: {"success": true, "message": "summary updated"}
    Example Args: {"text": "Great session, felt strong on bench"}
    """
    try:
        args = COACHBYTE_UPDATE_SummaryArgs(text=text)
        conn = _get_connection()
        try:
            cur = conn.cursor()
            log_id = _get_today_log_id(conn)
            cur.execute("UPDATE daily_logs SET summary = %s WHERE id = %s", (args.text, log_id))
            conn.commit()
            return (True, json.dumps({"success": True, "message": "summary updated"}))
        finally:
            conn.close()
    except Exception as e:
        return (False, f"Error updating summary: {str(e)}")


def COACHBYTE_GET_recent_history(days: int) -> Tuple[bool, str]:
    """Get recent workout history for N days (planned vs completed).
    Example Prompt: Show my last 7 days of workouts.
    Example Response: {"success": true, "history": [{"log_date": "2025-01-01", "exercise": "bench press", "reps": 10, "load": 135}]}
    Example Args: {"days": 7}
    """
    try:
        args = COACHBYTE_GET_RecentHistoryArgs(days=days)
        conn = _get_connection()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            start = date.today() - timedelta(days=args.days)
            cur.execute(
                """
                SELECT dl.log_date, e.name as exercise, ps.reps, ps.load, cs.reps_done, cs.load_done
                FROM planned_sets ps
                JOIN daily_logs dl ON ps.log_id = dl.id
                JOIN exercises e ON ps.exercise_id = e.id
                LEFT JOIN completed_sets cs ON cs.planned_set_id = ps.id
                WHERE dl.log_date >= %s
                ORDER BY dl.log_date, ps.order_num
                """,
                (start.isoformat(),),
            )
            rows = [dict(row) for row in cur.fetchall()]
            return (True, json.dumps({"success": True, "history": rows}))
        finally:
            conn.close()
    except Exception as e:
        return (False, f"Error getting history: {str(e)}")


def COACHBYTE_UPDATE_weekly_split_day(day: str, items: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Replace the weekly split plan for a specific day with provided sets.
    Example Prompt: Set Monday split to bench 5x at 80% 1RM and squat 10x185.
    Example Response: {"success": true, "message": "split updated for monday with 2 sets"}
    Example Args: {"day": "monday", "items": [{"exercise": "bench press", "reps": 5, "load": 0.8, "relative": true, "rest": 90, "order": 1}]}
    Notes: Use "relative": true with load as decimal (0.8 = 80% 1RM). Use "relative": false for absolute weight.
    """
    try:
        args = COACHBYTE_UPDATE_WeeklySplitDayArgs(day=day, items=items)
        key = args.day.lower()
        if key not in DAY_MAP:
            return (False, f"Invalid day: {args.day}")
        
        day_num = DAY_MAP[key]
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM split_sets WHERE day_of_week = %s", (day_num,))
            
            for item in args.items:
                ex_id = _get_exercise_id(conn, item.exercise)
                cur.execute(
                    "INSERT INTO split_sets (day_of_week, exercise_id, order_num, reps, load, rest, relative) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (day_num, ex_id, item.order, item.reps, item.load, item.rest, item.relative),
                )
            
            conn.commit()
            msg = f"split updated for {key} with {len(args.items)} sets"
            return (True, json.dumps({"success": True, "message": msg}))
        finally:
            conn.close()
    except Exception as e:
        return (False, f"Error updating split: {str(e)}")


def COACHBYTE_GET_weekly_split(day: Optional[str] = None) -> Tuple[bool, str]:
    """Get weekly split plan (all days or a specific day).
    Example Prompt: What's my Wednesday split?
    Example Response: {"success": true, "split": [{"exercise": "squats", "reps": 8, "load": 185, "rest": 120}]}
    Example Args: {"day": "wednesday"}
    """
    try:
        args = COACHBYTE_GET_WeeklySplitArgs(day=day)
        conn = _get_connection()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            if args.day is None:
                cur.execute(
                    "SELECT day_of_week, e.name as exercise, reps, load, rest, order_num, relative FROM split_sets ss JOIN exercises e ON ss.exercise_id = e.id ORDER BY day_of_week, order_num"
                )
            else:
                key = args.day.lower()
                if key not in DAY_MAP:
                    return (False, f"Invalid day: {args.day}")
                cur.execute(
                    "SELECT e.name as exercise, reps, load, rest, order_num, relative FROM split_sets ss JOIN exercises e ON ss.exercise_id = e.id WHERE day_of_week = %s ORDER BY order_num",
                    (DAY_MAP[key],),
                )
            
            rows = [dict(row) for row in cur.fetchall()]
            return (True, json.dumps({"success": True, "split": rows}))
        finally:
            conn.close()
    except Exception as e:
        return (False, f"Error getting split: {str(e)}")


def COACHBYTE_ACTION_set_timer(minutes: int) -> Tuple[bool, str]:
    """Set a rest/workout timer in minutes (1–180).
    Example Prompt: Set a 3 minute rest timer.
    Example Response: {"success": true, "message": "Timer set for 3 minutes"}
    Example Args: {"minutes": 3}
    """
    try:
        args = COACHBYTE_ACTION_SetTimerArgs(minutes=minutes)
        
        ext_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        timer_script = os.path.join(ext_root, "ui", "tools", "timer_temp.py")
        
        if not os.path.exists(timer_script):
            return (False, "Timer script not found")
        
        result = subprocess.run(
            ["python", timer_script, "set", str(args.minutes)],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(timer_script)
        )
        
        if result.returncode == 0:
            msg = f"Timer set for {args.minutes} minutes"
            return (True, json.dumps({"success": True, "message": msg}))
        else:
            return (False, f"Timer error: {result.stderr.strip()}")
    except Exception as e:
        return (False, f"Error setting timer: {str(e)}")


def COACHBYTE_GET_timer() -> Tuple[bool, str]:
    """Get current timer status and remaining time.
    Example Prompt: How much time is left on my rest timer?
    Example Response: {"success": true, "status": "running", "remaining_seconds": 120}
    Example Args: {}
    """
    try:
        ext_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        timer_script = os.path.join(ext_root, "ui", "tools", "timer_temp.py")
        
        if not os.path.exists(timer_script):
            return (False, "Timer script not found")
        
        result = subprocess.run(
            ["python", timer_script, "get"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(timer_script)
        )
        
        if result.returncode == 0:
            try:
                timer_data = json.loads(result.stdout.strip())
                timer_data["success"] = True
                return (True, json.dumps(timer_data))
            except json.JSONDecodeError:
                return (True, json.dumps({"success": True, "status": "no_timer", "message": result.stdout.strip()}))
        else:
            return (False, f"Timer error: {result.stderr.strip()}")
    except Exception as e:
        return (False, f"Error getting timer: {str(e)}")


# Export tools list
TOOLS = [
    COACHBYTE_UPDATE_new_daily_plan,
    COACHBYTE_GET_today_plan,
    COACHBYTE_ACTION_complete_next_set,
    COACHBYTE_ACTION_log_completed_set,
    COACHBYTE_UPDATE_summary,
    COACHBYTE_GET_recent_history,
    COACHBYTE_UPDATE_weekly_split_day,
    COACHBYTE_GET_weekly_split,
    COACHBYTE_ACTION_set_timer,
    COACHBYTE_GET_timer,
]

