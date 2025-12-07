#!/bin/bash

# Path to your text file
TEXT_FILE="$HOME/.config/scripts/dhikr.txt"

# Check if file exists
if [ ! -f "$TEXT_FILE" ]; then
    echo "No quotes file found"
    exit 0
fi

# Check if file is empty
if [ ! -s "$TEXT_FILE" ]; then
    echo "Quotes file is empty"
    exit 0
fi

# Get a random non-empty line using shuf
shuf -n 1 "$TEXT_FILE"
