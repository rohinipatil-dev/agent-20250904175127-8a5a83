#!/bin/bash
            set -e
            echo "Starting build.sh..."
            echo "Installing dependencies..."
            pip install --upgrade pip
            pip install -r requirements.txt
        