"""
CoachByte API Service

Publicly exposed API service for workout tracking.
Wraps the COACHBYTE_ACTION_complete_next_set tool as a REST endpoint.
"""
import os
import sys
import argparse
from pathlib import Path

# Add repo root to path for imports
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load .env from repo root
try:
    from dotenv import load_dotenv
    env_path = REPO_ROOT / ".env"
    load_dotenv(env_path)
except Exception:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

# Import the auth middleware
from core.utils.service_auth import APIKeyMiddleware, get_service_api_key

# Import the actual tool function
from extensions.coachbyte.tools.coachbyte_tools import COACHBYTE_ACTION_complete_next_set

app = FastAPI(
    title="CoachByte API",
    description="Public API for CoachByte workout tracking",
    version="1.0.0"
)

# Add CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class CompleteSetRequest(BaseModel):
    """Request body for completing a set"""
    exercise: Optional[str] = Field(None, description="Specific exercise to complete (optional)")
    reps: Optional[int] = Field(None, ge=1, le=100, description="Override reps (optional)")
    load: Optional[float] = Field(None, ge=0, le=2000, description="Override load (optional)")


class CompleteSetResponse(BaseModel):
    """Response from completing a set"""
    success: bool
    message: str
    data: Optional[dict] = None


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "coachbyte-api"}


@app.post("/complete-set", response_model=CompleteSetResponse)
async def complete_set(request: CompleteSetRequest):
    """
    Complete the next planned workout set.

    - **exercise**: Optional - specify which exercise to complete
    - **reps**: Optional - override the planned reps
    - **load**: Optional - override the planned load
    """
    try:
        # Call the underlying tool
        success, json_result = COACHBYTE_ACTION_complete_next_set(
            exercise=request.exercise,
            reps=request.reps,
            load=request.load
        )

        # Parse the JSON response
        import json
        try:
            data = json.loads(json_result)
        except (json.JSONDecodeError, TypeError):
            data = {"raw": json_result}

        return CompleteSetResponse(
            success=success,
            message=data.get("message", "Set completed") if isinstance(data, dict) else str(data),
            data=data if isinstance(data, dict) else None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "service": "CoachByte API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check",
            "/complete-set": "POST - Complete next workout set",
            "/docs": "Interactive API documentation"
        }
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, required=True, help="Port to bind to")
    args = parser.parse_args()

    # Get API key from environment
    api_key = get_service_api_key("coachbyte", "api")
    if not api_key:
        print("[ERROR] SERVICE_COACHBYTE_API_API_KEY not found in environment")
        sys.exit(1)

    print(f"[CoachByte API] Starting server on {args.host}:{args.port}")
    print(f"[CoachByte API] API Key authentication enabled")
    print(f"[CoachByte API] Public URL: https://{os.getenv('PUBLIC_DOMAIN', 'localhost')}/api/coachbyte")
    print(f"[CoachByte API] Docs: https://{os.getenv('PUBLIC_DOMAIN', 'localhost')}/api/coachbyte/docs")

    # Add API key middleware
    app.add_middleware(APIKeyMiddleware, api_key=api_key)

    # Run server
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
