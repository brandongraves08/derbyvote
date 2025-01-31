#!/bin/bash
# Install gunicorn
/usr/bin/python3 -m pip install --user gunicorn

# Add local bin to PATH
export PATH=$PATH:$HOME/.local/bin

# Start gunicorn using Python module
exec /usr/bin/python3 -m gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 4 --timeout 120 app:app
