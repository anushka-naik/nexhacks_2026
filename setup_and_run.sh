#!/bin/bash

# Setup and Run Script for Overshoot Demo

echo "==========================================="
echo "   Overshoot Demo - Setup & Instructions   "
echo "==========================================="

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed."
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

echo ""
echo "[1/2] Setting up Backend..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

echo "Installing backend dependencies..."
pip install -r requirements.txt

echo "Backend setup complete."
cd ..

echo ""
echo "[2/2] Setting up Frontend..."
echo "Installing frontend dependencies..."
npm install

echo ""
echo "==========================================="
echo "           SETUP COMPLETE                  "
echo "==========================================="
echo ""
echo "To run the project, you need two terminal windows:"
echo ""
echo "Terminal 1 (Backend):"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  python app.py"
echo ""
echo "Terminal 2 (Frontend):"
echo "  npx vite"
echo ""
echo "Then open your browser to the URL shown by Vite (usually http://localhost:5173)"
