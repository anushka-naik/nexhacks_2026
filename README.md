# Overshoot Realtime Vision Demo

This project demonstrates a realtime vision application using the Overshoot SDK, with a Python Flask backend for graph storage (Neo4j) and a frontend demo.

## Prerequisites

- Node.js (v18+ recommended)
- Python 3.9+
- Neo4j Database (Credentials are currently hardcoded in `backend/app.py` and `db.js`)

## Project Structure

- `backend/`: Python Flask application.
  - `app.py`: Main API entry point.
  - `graph_store.py`: Neo4j interaction logic.
- `web/`: Next.js application (Build artifacts only currently).
- `demo.js` & `index.html`: Frontend demo using Overshoot SDK.
- `db.js`: Standalone Neo4j connection script (currently unused in demo).

## Setup & Execution

### 1. Backend (Flask API)

The backend handles data storage and retrieval from Neo4j.

```bash
# Navigate to backend directory
cd backend

# Create a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The backend will start at `http://0.0.0.0:5000`.

**Test Backend Health:**
```bash
curl http://localhost:5000/health
```

### 2. Frontend (Overshoot Demo)

The frontend captures video and uses Overshoot SDK to analyze it.

```bash
# Navigate to root directory
cd .

# Install dependencies
npm install

# Start the development server
npx vite
```

The frontend will start at `http://localhost:5173` (or another port if 5173 is busy).

**Usage:**
1. Open the URL in your browser.
2. Click **Start Camera**.
3. Allow camera access.
4. The application will process video frames and display results.

## Testing

- **Backend Tests:** currently manual verification via API endpoints.
- **Frontend Tests:** manual verification via the browser interface.

## iMessage Notifications (macOS Only)

This project can send an iMessage to your phone whenever an observation is stored, and also exposes a demo endpoint for testing.

### 1. Install Node Dependencies

From the project root:

```bash
cd /Users/aishwaryabirla/Documents/trae_projects/nexhacks
npm install
```

This installs `@photon-ai/imessage-kit` and its dependencies.

### 2. Configure macOS Permissions

`imessage-kit` needs access to the Messages database and the Messages app:

- Open **System Settings → Privacy & Security → Full Disk Access**
- Click **“+”** and add the terminal/IDE you use (e.g. **Terminal**, **iTerm**, **VS Code**, **Cursor**)
- Ensure the toggle is **enabled** for that app
- Quit and reopen the terminal/IDE after enabling access

Also ensure:

- The **Messages** app is open and running
- You are signed in with your Apple ID and iMessage is enabled
- You can manually send a message to the phone/email you plan to use

### 3. Set Destination Phone / Email

In the same shell where you run the backend, set:

```bash
export IMESSAGE_PHONE="+1XXXXXXXXXX"   # or your iMessage email
```

The value must be an iMessage-capable address already working in the Messages app.

### 4. Run the Dummy iMessage Backend

There is a minimal backend dedicated to testing iMessage sending:

```bash
cd backend
python imessage_demo_app.py
```

This starts a Flask server on `http://localhost:5001` with:

- `GET /health`
- `GET/POST /demo-imessage`

### 5. Send a Demo iMessage

In another terminal:

```bash
curl "http://localhost:5001/demo-imessage?user_id=demo&message=Hello%20from%20debug"
```

If everything is configured correctly you should:

- See `"success": true` in the JSON response
- Receive an iMessage on your phone with the given message

If `"success": false`, check the `stderr` field in the JSON for a detailed error message from `imessage-kit` (e.g., Messages app not running, permissions, etc.).

### 6. Observation-Triggered iMessages (Main Backend)

The main backend in `backend/app.py` also sends an iMessage whenever `/observation` is called successfully.

- Backend: `python backend/app.py` (on port `5000`)
- Endpoint: `POST /observation`
  - After storing the observation, it triggers `imessage_notify.js` with the configured `IMESSAGE_PHONE`.

To use this:

1. Complete steps 1–3 above
2. Run the main backend
3. Hit `POST /observation` from the frontend or via `curl`

## Notes

- `demo.js` currently calls OpenAI API directly for data transformation.
- Ensure you have valid API keys if replacing the hardcoded ones.
