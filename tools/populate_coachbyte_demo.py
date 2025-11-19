#!/usr/bin/env python3
"""Populate CoachByte with demo data for a week of workouts."""

import sys
import os
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
import uuid
import random

# Add repo root to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

# Load environment from .env
from dotenv import load_dotenv
load_dotenv(repo_root / ".env")

# Import CoachByte tools
from extensions.coachbyte.tools.coachbyte_tools import (
    COACHBYTE_UPDATE_weekly_split_day,
    _get_connection,
    _get_exercise_id,
)

import psycopg2
import psycopg2.extras


def create_split():
    """Create an expanded Push/Pull/Legs split."""
    print("Creating expanded weekly split...")

    # Monday: Push Day
    monday_sets = [
        # Main compound
        {"exercise": "Bench Press", "reps": 5, "load": 0.85, "relative": True, "rest": 180, "order": 1},
        {"exercise": "Bench Press", "reps": 5, "load": 0.85, "relative": True, "rest": 180, "order": 2},
        {"exercise": "Bench Press", "reps": 5, "load": 0.85, "relative": True, "rest": 180, "order": 3},
        # Secondary compound
        {"exercise": "Overhead Press", "reps": 8, "load": 0.75, "relative": True, "rest": 120, "order": 4},
        {"exercise": "Overhead Press", "reps": 8, "load": 0.75, "relative": True, "rest": 120, "order": 5},
        {"exercise": "Overhead Press", "reps": 8, "load": 0.75, "relative": True, "rest": 120, "order": 6},
        # Accessories
        {"exercise": "Incline Dumbbell Press", "reps": 10, "load": 70, "relative": False, "rest": 90, "order": 7},
        {"exercise": "Incline Dumbbell Press", "reps": 10, "load": 70, "relative": False, "rest": 90, "order": 8},
        {"exercise": "Incline Dumbbell Press", "reps": 10, "load": 70, "relative": False, "rest": 90, "order": 9},
        {"exercise": "Dips", "reps": 12, "load": 0, "relative": False, "rest": 90, "order": 10},
        {"exercise": "Dips", "reps": 12, "load": 0, "relative": False, "rest": 90, "order": 11},
        {"exercise": "Dips", "reps": 12, "load": 0, "relative": False, "rest": 90, "order": 12},
        {"exercise": "Lateral Raises", "reps": 12, "load": 20, "relative": False, "rest": 60, "order": 13},
        {"exercise": "Lateral Raises", "reps": 12, "load": 20, "relative": False, "rest": 60, "order": 14},
        {"exercise": "Lateral Raises", "reps": 12, "load": 20, "relative": False, "rest": 60, "order": 15},
        {"exercise": "Tricep Extensions", "reps": 12, "load": 50, "relative": False, "rest": 60, "order": 16},
        {"exercise": "Tricep Extensions", "reps": 12, "load": 50, "relative": False, "rest": 60, "order": 17},
        {"exercise": "Tricep Extensions", "reps": 12, "load": 50, "relative": False, "rest": 60, "order": 18},
    ]
    success, result = COACHBYTE_UPDATE_weekly_split_day("monday", monday_sets)
    print(f"  Monday: {len(monday_sets)} sets")

    # Tuesday: Pull Day
    tuesday_sets = [
        # Main compound
        {"exercise": "Deadlift", "reps": 5, "load": 0.85, "relative": True, "rest": 240, "order": 1},
        {"exercise": "Deadlift", "reps": 5, "load": 0.85, "relative": True, "rest": 240, "order": 2},
        {"exercise": "Deadlift", "reps": 5, "load": 0.85, "relative": True, "rest": 240, "order": 3},
        # Secondary compound
        {"exercise": "Barbell Row", "reps": 8, "load": 0.75, "relative": True, "rest": 120, "order": 4},
        {"exercise": "Barbell Row", "reps": 8, "load": 0.75, "relative": True, "rest": 120, "order": 5},
        {"exercise": "Barbell Row", "reps": 8, "load": 0.75, "relative": True, "rest": 120, "order": 6},
        # Accessories
        {"exercise": "Pull-ups", "reps": 10, "load": 0, "relative": False, "rest": 90, "order": 7},
        {"exercise": "Pull-ups", "reps": 10, "load": 0, "relative": False, "rest": 90, "order": 8},
        {"exercise": "Pull-ups", "reps": 10, "load": 0, "relative": False, "rest": 90, "order": 9},
        {"exercise": "Lat Pulldown", "reps": 12, "load": 140, "relative": False, "rest": 90, "order": 10},
        {"exercise": "Lat Pulldown", "reps": 12, "load": 140, "relative": False, "rest": 90, "order": 11},
        {"exercise": "Lat Pulldown", "reps": 12, "load": 140, "relative": False, "rest": 90, "order": 12},
        {"exercise": "Face Pulls", "reps": 15, "load": 60, "relative": False, "rest": 60, "order": 13},
        {"exercise": "Face Pulls", "reps": 15, "load": 60, "relative": False, "rest": 60, "order": 14},
        {"exercise": "Face Pulls", "reps": 15, "load": 60, "relative": False, "rest": 60, "order": 15},
        {"exercise": "Barbell Curl", "reps": 12, "load": 60, "relative": False, "rest": 60, "order": 16},
        {"exercise": "Barbell Curl", "reps": 12, "load": 60, "relative": False, "rest": 60, "order": 17},
        {"exercise": "Barbell Curl", "reps": 12, "load": 60, "relative": False, "rest": 60, "order": 18},
    ]
    success, result = COACHBYTE_UPDATE_weekly_split_day("tuesday", tuesday_sets)
    print(f"  Tuesday: {len(tuesday_sets)} sets")

    # Wednesday: Leg Day
    wednesday_sets = [
        # Main compound
        {"exercise": "Squat", "reps": 5, "load": 0.85, "relative": True, "rest": 240, "order": 1},
        {"exercise": "Squat", "reps": 5, "load": 0.85, "relative": True, "rest": 240, "order": 2},
        {"exercise": "Squat", "reps": 5, "load": 0.85, "relative": True, "rest": 240, "order": 3},
        # Secondary compound
        {"exercise": "Romanian Deadlift", "reps": 10, "load": 0.65, "relative": True, "rest": 120, "order": 4},
        {"exercise": "Romanian Deadlift", "reps": 10, "load": 0.65, "relative": True, "rest": 120, "order": 5},
        {"exercise": "Romanian Deadlift", "reps": 10, "load": 0.65, "relative": True, "rest": 120, "order": 6},
        # Accessories
        {"exercise": "Leg Press", "reps": 15, "load": 315, "relative": False, "rest": 90, "order": 7},
        {"exercise": "Leg Press", "reps": 15, "load": 315, "relative": False, "rest": 90, "order": 8},
        {"exercise": "Leg Press", "reps": 15, "load": 315, "relative": False, "rest": 90, "order": 9},
        {"exercise": "Leg Curl", "reps": 12, "load": 90, "relative": False, "rest": 60, "order": 10},
        {"exercise": "Leg Curl", "reps": 12, "load": 90, "relative": False, "rest": 60, "order": 11},
        {"exercise": "Leg Curl", "reps": 12, "load": 90, "relative": False, "rest": 60, "order": 12},
        {"exercise": "Calf Raises", "reps": 15, "load": 180, "relative": False, "rest": 60, "order": 13},
        {"exercise": "Calf Raises", "reps": 15, "load": 180, "relative": False, "rest": 60, "order": 14},
        {"exercise": "Calf Raises", "reps": 15, "load": 180, "relative": False, "rest": 60, "order": 15},
        {"exercise": "Leg Extensions", "reps": 12, "load": 100, "relative": False, "rest": 60, "order": 16},
        {"exercise": "Leg Extensions", "reps": 12, "load": 100, "relative": False, "rest": 60, "order": 17},
        {"exercise": "Leg Extensions", "reps": 12, "load": 100, "relative": False, "rest": 60, "order": 18},
    ]
    success, result = COACHBYTE_UPDATE_weekly_split_day("wednesday", wednesday_sets)
    print(f"  Wednesday: {len(wednesday_sets)} sets")

    # Thursday: Rest
    success, result = COACHBYTE_UPDATE_weekly_split_day("thursday", [])
    print(f"  Thursday: Rest day")

    # Friday: Push Day 2
    friday_sets = [
        # Main compound variation
        {"exercise": "Incline Bench Press", "reps": 8, "load": 0.75, "relative": True, "rest": 150, "order": 1},
        {"exercise": "Incline Bench Press", "reps": 8, "load": 0.75, "relative": True, "rest": 150, "order": 2},
        {"exercise": "Incline Bench Press", "reps": 8, "load": 0.75, "relative": True, "rest": 150, "order": 3},
        # Secondary
        {"exercise": "Dumbbell Shoulder Press", "reps": 10, "load": 60, "relative": False, "rest": 120, "order": 4},
        {"exercise": "Dumbbell Shoulder Press", "reps": 10, "load": 60, "relative": False, "rest": 120, "order": 5},
        {"exercise": "Dumbbell Shoulder Press", "reps": 10, "load": 60, "relative": False, "rest": 120, "order": 6},
        # Accessories
        {"exercise": "Cable Flyes", "reps": 12, "load": 30, "relative": False, "rest": 60, "order": 7},
        {"exercise": "Cable Flyes", "reps": 12, "load": 30, "relative": False, "rest": 60, "order": 8},
        {"exercise": "Cable Flyes", "reps": 12, "load": 30, "relative": False, "rest": 60, "order": 9},
        {"exercise": "Lateral Raises", "reps": 12, "load": 20, "relative": False, "rest": 60, "order": 10},
        {"exercise": "Lateral Raises", "reps": 12, "load": 20, "relative": False, "rest": 60, "order": 11},
        {"exercise": "Lateral Raises", "reps": 12, "load": 20, "relative": False, "rest": 60, "order": 12},
        {"exercise": "Tricep Pushdown", "reps": 15, "load": 70, "relative": False, "rest": 60, "order": 13},
        {"exercise": "Tricep Pushdown", "reps": 15, "load": 70, "relative": False, "rest": 60, "order": 14},
        {"exercise": "Tricep Pushdown", "reps": 15, "load": 70, "relative": False, "rest": 60, "order": 15},
        {"exercise": "Overhead Tricep Extensions", "reps": 12, "load": 50, "relative": False, "rest": 60, "order": 16},
        {"exercise": "Overhead Tricep Extensions", "reps": 12, "load": 50, "relative": False, "rest": 60, "order": 17},
        {"exercise": "Overhead Tricep Extensions", "reps": 12, "load": 50, "relative": False, "rest": 60, "order": 18},
    ]
    success, result = COACHBYTE_UPDATE_weekly_split_day("friday", friday_sets)
    print(f"  Friday: {len(friday_sets)} sets")

    # Saturday: Pull Day 2
    saturday_sets = [
        # Main
        {"exercise": "Lat Pulldown", "reps": 10, "load": 150, "relative": False, "rest": 90, "order": 1},
        {"exercise": "Lat Pulldown", "reps": 10, "load": 150, "relative": False, "rest": 90, "order": 2},
        {"exercise": "Lat Pulldown", "reps": 10, "load": 150, "relative": False, "rest": 90, "order": 3},
        {"exercise": "Lat Pulldown", "reps": 10, "load": 150, "relative": False, "rest": 90, "order": 4},
        # Secondary
        {"exercise": "Cable Row", "reps": 12, "load": 120, "relative": False, "rest": 90, "order": 5},
        {"exercise": "Cable Row", "reps": 12, "load": 120, "relative": False, "rest": 90, "order": 6},
        {"exercise": "Cable Row", "reps": 12, "load": 120, "relative": False, "rest": 90, "order": 7},
        # Accessories
        {"exercise": "T-Bar Row", "reps": 10, "load": 90, "relative": False, "rest": 90, "order": 8},
        {"exercise": "T-Bar Row", "reps": 10, "load": 90, "relative": False, "rest": 90, "order": 9},
        {"exercise": "T-Bar Row", "reps": 10, "load": 90, "relative": False, "rest": 90, "order": 10},
        {"exercise": "Face Pulls", "reps": 15, "load": 60, "relative": False, "rest": 60, "order": 11},
        {"exercise": "Face Pulls", "reps": 15, "load": 60, "relative": False, "rest": 60, "order": 12},
        {"exercise": "Face Pulls", "reps": 15, "load": 60, "relative": False, "rest": 60, "order": 13},
        {"exercise": "Hammer Curls", "reps": 12, "load": 35, "relative": False, "rest": 60, "order": 14},
        {"exercise": "Hammer Curls", "reps": 12, "load": 35, "relative": False, "rest": 60, "order": 15},
        {"exercise": "Hammer Curls", "reps": 12, "load": 35, "relative": False, "rest": 60, "order": 16},
        {"exercise": "Barbell Curl", "reps": 10, "load": 65, "relative": False, "rest": 60, "order": 17},
        {"exercise": "Barbell Curl", "reps": 10, "load": 65, "relative": False, "rest": 60, "order": 18},
    ]
    success, result = COACHBYTE_UPDATE_weekly_split_day("saturday", saturday_sets)
    print(f"  Saturday: {len(saturday_sets)} sets")

    # Sunday: Rest
    success, result = COACHBYTE_UPDATE_weekly_split_day("sunday", [])
    print(f"  Sunday: Rest day")

    print("\n✓ Weekly split created successfully!")


def populate_historical_workouts():
    """Populate the past week with historical completed workouts using direct SQL."""
    print("\nPopulating historical workout data...")

    conn = _get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    today = date.today()

    # Historical workout plans for past 7 days
    # Format: (days_ago, day_name, [(exercise, reps, load, completed_reps, completed_load), ...])
    historical_workouts = [
        # 7 days ago - Monday Push
        (7, "monday", [
            ("Bench Press", 5, 225, 5, 225),
            ("Bench Press", 5, 225, 5, 225),
            ("Bench Press", 5, 225, 4, 225),  # Failed last rep
            ("Overhead Press", 8, 135, 8, 135),
            ("Overhead Press", 8, 135, 8, 135),
            ("Overhead Press", 8, 135, 7, 135),  # One rep short
            ("Incline Dumbbell Press", 10, 70, 10, 70),
            ("Incline Dumbbell Press", 10, 70, 10, 70),
            ("Incline Dumbbell Press", 10, 70, 9, 70),
            ("Dips", 12, 0, 12, 0),
            ("Dips", 12, 0, 11, 0),
            ("Dips", 12, 0, 10, 0),
            ("Lateral Raises", 12, 20, 12, 20),
            ("Lateral Raises", 12, 20, 12, 20),
            ("Lateral Raises", 12, 20, 12, 20),
            ("Tricep Extensions", 12, 50, 12, 50),
            ("Tricep Extensions", 12, 50, 12, 50),
            ("Tricep Extensions", 12, 50, 11, 50),
        ]),

        # 6 days ago - Tuesday Pull
        (6, "tuesday", [
            ("Deadlift", 5, 315, 5, 315),
            ("Deadlift", 5, 315, 5, 315),
            ("Deadlift", 5, 315, 5, 315),
            ("Barbell Row", 8, 185, 8, 185),
            ("Barbell Row", 8, 185, 8, 185),
            ("Barbell Row", 8, 185, 7, 185),
            ("Pull-ups", 10, 0, 10, 0),
            ("Pull-ups", 10, 0, 9, 0),
            ("Pull-ups", 10, 0, 8, 0),
            ("Lat Pulldown", 12, 140, 12, 140),
            ("Lat Pulldown", 12, 140, 12, 140),
            ("Lat Pulldown", 12, 140, 12, 140),
            ("Face Pulls", 15, 60, 15, 60),
            ("Face Pulls", 15, 60, 15, 60),
            ("Face Pulls", 15, 60, 15, 60),
            ("Barbell Curl", 12, 60, 12, 60),
            ("Barbell Curl", 12, 60, 11, 60),
            ("Barbell Curl", 12, 60, 10, 60),
        ]),

        # 5 days ago - Wednesday Legs
        (5, "wednesday", [
            ("Squat", 5, 275, 5, 275),
            ("Squat", 5, 275, 5, 275),
            ("Squat", 5, 275, 5, 275),
            ("Romanian Deadlift", 10, 205, 10, 205),
            ("Romanian Deadlift", 10, 205, 10, 205),
            ("Romanian Deadlift", 10, 205, 10, 205),
            ("Leg Press", 15, 315, 15, 315),
            ("Leg Press", 15, 315, 15, 315),
            ("Leg Press", 15, 315, 14, 315),
            ("Leg Curl", 12, 90, 12, 90),
            ("Leg Curl", 12, 90, 12, 90),
            ("Leg Curl", 12, 90, 12, 90),
            ("Calf Raises", 15, 180, 15, 180),
            ("Calf Raises", 15, 180, 15, 180),
            ("Calf Raises", 15, 180, 15, 180),
            ("Leg Extensions", 12, 100, 12, 100),
            ("Leg Extensions", 12, 100, 12, 100),
            ("Leg Extensions", 12, 100, 11, 100),
        ]),

        # 3 days ago - Friday Push
        (3, "friday", [
            ("Incline Bench Press", 8, 185, 8, 185),
            ("Incline Bench Press", 8, 185, 8, 185),
            ("Incline Bench Press", 8, 185, 7, 185),
            ("Dumbbell Shoulder Press", 10, 60, 10, 60),
            ("Dumbbell Shoulder Press", 10, 60, 10, 60),
            ("Dumbbell Shoulder Press", 10, 60, 9, 60),
            ("Cable Flyes", 12, 30, 12, 30),
            ("Cable Flyes", 12, 30, 12, 30),
            ("Cable Flyes", 12, 30, 12, 30),
            ("Lateral Raises", 12, 20, 12, 20),
            ("Lateral Raises", 12, 20, 12, 20),
            ("Lateral Raises", 12, 20, 11, 20),
            ("Tricep Pushdown", 15, 70, 15, 70),
            ("Tricep Pushdown", 15, 70, 15, 70),
            ("Tricep Pushdown", 15, 70, 14, 70),
            ("Overhead Tricep Extensions", 12, 50, 12, 50),
            ("Overhead Tricep Extensions", 12, 50, 12, 50),
            ("Overhead Tricep Extensions", 12, 50, 11, 50),
        ]),

        # 2 days ago - Saturday Pull
        (2, "saturday", [
            ("Lat Pulldown", 10, 150, 10, 150),
            ("Lat Pulldown", 10, 150, 10, 150),
            ("Lat Pulldown", 10, 150, 10, 150),
            ("Lat Pulldown", 10, 150, 9, 150),
            ("Cable Row", 12, 120, 12, 120),
            ("Cable Row", 12, 120, 12, 120),
            ("Cable Row", 12, 120, 12, 120),
            ("T-Bar Row", 10, 90, 10, 90),
            ("T-Bar Row", 10, 90, 10, 90),
            ("T-Bar Row", 10, 90, 9, 90),
            ("Face Pulls", 15, 60, 15, 60),
            ("Face Pulls", 15, 60, 15, 60),
            ("Face Pulls", 15, 60, 15, 60),
            ("Hammer Curls", 12, 35, 12, 35),
            ("Hammer Curls", 12, 35, 12, 35),
            ("Hammer Curls", 12, 35, 11, 35),
            ("Barbell Curl", 10, 65, 10, 65),
            ("Barbell Curl", 10, 65, 10, 65),
        ]),
    ]

    summaries = {
        7: "Solid push session. Bench felt strong, missed last rep on final set. Good pump on accessories.",
        6: "Great deadlift day! All sets felt smooth. Pull-ups getting easier.",
        5: "Tough leg day but got through it. Squats moving well at this weight.",
        3: "Incline bench going up nicely. Shoulders feeling good. Light pump work felt great.",
        2: "High volume pull day. Lats are fried. Good progression on lat pulldown.",
    }

    try:
        for days_ago, day_name, workout in historical_workouts:
            workout_date = today - timedelta(days=days_ago)
            log_id = str(uuid.uuid4())

            # Create daily log
            cur.execute(
                "INSERT INTO daily_logs (id, log_date, summary) VALUES (%s, %s, %s)",
                (log_id, workout_date.isoformat(), summaries.get(days_ago, ""))
            )

            # Create planned and completed sets
            for idx, (exercise, planned_reps, planned_load, completed_reps, completed_load) in enumerate(workout, 1):
                exercise_id = _get_exercise_id(conn, exercise)

                # Insert planned set
                planned_set_id = cur.execute(
                    "INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load, rest) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                    (log_id, exercise_id, idx, planned_reps, planned_load, 90)
                )
                planned_set_id = cur.fetchone()['id']

                # Insert completed set with slight time variation
                completed_time = datetime.combine(workout_date, datetime.min.time()).replace(
                    hour=10 + (idx // 10),  # Spread across workout time
                    minute=(idx * 3) % 60,
                    tzinfo=timezone.utc
                )

                cur.execute(
                    "INSERT INTO completed_sets (log_id, exercise_id, planned_set_id, reps_done, load_done, completed_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (log_id, exercise_id, planned_set_id, completed_reps, completed_load, completed_time)
                )

            conn.commit()
            print(f"  ✓ {workout_date.isoformat()} ({day_name}): {len(workout)} sets completed")

        print(f"\n✓ Historical workout data populated successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error populating historical data: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("CoachByte Demo Data Population")
    print("=" * 60)
    print()

    try:
        # Create the weekly split
        create_split()

        # Populate historical workouts
        populate_historical_workouts()

        print("\n" + "=" * 60)
        print("Demo data setup complete!")
        print("=" * 60)
        print("\nDemo includes:")
        print("• Push/Pull/Legs/Rest split (18 sets per workout)")
        print("• 5 completed workouts over past 7 days")
        print("• Realistic rep/load variations (some sets failed)")
        print("• PR data from completed sets")
        print("\nNext steps:")
        print("1. Open the CoachByte UI")
        print("2. View past workouts and progression")
        print("3. Check PR tracker for exercise records")
        print("4. Today's workout will auto-populate from split")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
