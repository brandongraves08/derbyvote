#!/bin/bash
# Install gunicorn
pip3 install --user gunicorn

# Add local bin to PATH
export PATH=$PATH:$HOME/.local/bin

# Start gunicorn
$HOME/.local/bin/gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 4 --timeout 120 app:app
