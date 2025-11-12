#!/bin/bash
# Start CoachByte UI on specified port
PORT=${1:-5200}
export PORT=$PORT

# Start Vite dev server on the provided port
# NOTE: Backend API calls go through Caddy at /api/coachbyte
# (no need to export backend port - Caddy handles routing)
npm run dev

