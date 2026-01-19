#!/bin/bash

# Ensure media directory exists and is writable
mkdir -p /app/media
chmod 777 /app/media 2>/dev/null || true

# Run the main command
exec "$@"
