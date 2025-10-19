#!/bin/bash
PORT=$1

# Set environment variable for the server
export PORT=$PORT

# Start the Express server
node server.js

