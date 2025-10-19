# CoachByte Extension

CoachByte is a comprehensive workout tracking and planning extension for Luna.

## Features

- **Daily Workout Planning**: Create and manage daily workout plans with exercises, sets, reps, and loads
- **Progress Tracking**: Log completed sets and track your workout history
- **Weekly Split Management**: Define and manage weekly workout splits for different days
- **Timer Functionality**: Built-in rest timer to help manage rest periods between sets
- **Personal Records**: Track PRs for different exercises and rep ranges
- **Workout History**: View recent workout history and summaries

## Requirements

This extension requires a PostgreSQL database. Set the `DATABASE_URL` environment variable in your `.env` file:

```
DATABASE_URL=postgresql://user:password@host:port/database
```

## Components

- **Tools**: Agent-accessible functions for workout planning and tracking
- **UI**: React-based web interface for manual workout management
- **Backend Service**: Express server providing REST API for the UI

## Usage

The extension provides tools that can be used by Luna agents to help plan and track workouts. Users can also interact directly with the UI for manual entry and visualization of workout data.

