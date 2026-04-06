#!/bin/bash
# Setup and run icloudpd Menubar Monitor

cd "$(dirname "$0")"

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "Erstelle virtuelle Umgebung..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install deps
echo "Installiere Abhängigkeiten..."
pip install -q -r requirements.txt

echo "Starte icloudpd Monitor..."
python3 app.py
