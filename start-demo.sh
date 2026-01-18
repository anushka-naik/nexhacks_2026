#!/bin/bash

# Second Brain Demo Startup Script
# This script starts both backend and frontend in separate terminal tabs

echo "🧠 Starting Second Brain Demo..."
echo ""

# Check if we're on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 Detected macOS - Opening new Terminal tabs..."

    # Open new tab for backend (with venv activation)
    osascript <<EOF
tell application "Terminal"
    activate
    tell application "System Events" to keystroke "t" using command down
    delay 0.5
    do script "cd \"$PWD/backend\" && echo '🔧 Starting Backend (activating venv)...' && source .venv/bin/activate && python app.py" in front window
end tell
EOF

    sleep 1

    # Open new tab for frontend
    osascript <<EOF
tell application "Terminal"
    activate
    tell application "System Events" to keystroke "t" using command down
    delay 0.5
    do script "cd \"$PWD\" && echo '🎨 Starting Frontend...' && npm run dev" in front window
end tell
EOF

    echo "✅ Started backend and frontend in new tabs"
    echo ""
    echo "📍 Backend: http://localhost:5000"
    echo "📍 Frontend: http://localhost:5173"
    echo ""
    echo "👉 Open http://localhost:5173 in your browser"

else
    # For Linux, use gnome-terminal or fallback to background processes
    echo "🐧 Detected Linux..."

    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --tab --title="Backend" -- bash -c "cd backend && echo '🔧 Starting Backend...' && source .venv/bin/activate && python app.py; exec bash"
        gnome-terminal --tab --title="Frontend" -- bash -c "echo '🎨 Starting Frontend...' && npm run dev; exec bash"
        echo "✅ Started in new gnome-terminal tabs"
    else
        echo "Starting processes in background..."
        cd backend && source .venv/bin/activate && python app.py > ../backend.log 2>&1 &
        BACKEND_PID=$!
        cd ..
        npm run dev > frontend.log 2>&1 &
        FRONTEND_PID=$!

        echo "✅ Backend PID: $BACKEND_PID (log: backend.log)"
        echo "✅ Frontend PID: $FRONTEND_PID (log: frontend.log)"
        echo ""
        echo "To stop: kill $BACKEND_PID $FRONTEND_PID"
    fi

    echo ""
    echo "📍 Backend: http://localhost:5000"
    echo "📍 Frontend: http://localhost:5173"
    echo ""
    echo "👉 Open http://localhost:5173 in your browser"
fi
