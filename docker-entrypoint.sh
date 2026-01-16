#!/bin/bash
set -e

# Initialize config if directory is empty
if [ -z "$(ls -A /etc/roxx)" ]; then
    echo "Initializing configuration..."
    # Copy default templates if we had them, otherwise just warn
    echo "Warning: /etc/roxx is empty. Please run setup wizard."
fi

# Start FreeRADIUS in background (if configured)
if [ -f /etc/freeradius/3.0/radiusd.conf ]; then
    echo "Starting FreeRADIUS..."
    service freeradius start
fi

# Execute command
exec "$@"
