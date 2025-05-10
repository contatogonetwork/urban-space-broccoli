#!/bin/bash
set -e  # Exit immediately if a command fails

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
cd "$SCRIPT_DIR"  # Ensure we're in the script directory

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found in $(pwd)"
    exit 1
fi

echo "Checking for requirements.txt..."
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "requirements.txt not found. Installing basic dependencies..."
    pip install streamlit pandas
fi

echo "Dependencies installed."
echo "Executing Streamlit app (app.py)..."

# Run the Streamlit app
streamlit run app.py
