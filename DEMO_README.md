# Second Brain - Hackathon Demo Guide 🧠

A real-time "second brain" system that captures video streams, builds a knowledge graph, and provides proactive suggestions.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (demo.js)                    │
│  Camera → Overshoot Vision → GPT-4o Transform → Backend │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  BACKEND (Flask API)                     │
│  Semantic Router → Token Compression → Neo4j Storage    │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              NEO4J KNOWLEDGE GRAPH                       │
│  Events → Entities → Memories → Routines               │
└─────────────────────────────────────────────────────────┘
```

## Quick Start (2 Terminals)

### Terminal 1: Backend

```bash
cd backend
source .venv/bin/activate  # Activate virtual environment
python app.py
```

Backend starts on: **http://localhost:5000**

### Terminal 2: Frontend

```bash
npm install
npm run dev
```

Frontend starts on: **http://localhost:5173** (Vite default)

## Full Setup Instructions

### 1. Backend Setup

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Verify .env file exists with:
# - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
# - TOKENC_API_KEY

# Start Flask server
python app.py
```

**Expected Output:**
```
[GraphStore] Using database: neo4j
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
```

### 2. Frontend Setup

```bash
# From project root
npm install

# Start Vite dev server
npm run dev
```

**Expected Output:**
```
VITE v7.3.1  ready in 234 ms
➜  Local:   http://localhost:5173/
```

### 3. Open Demo

Open browser to: **http://localhost:5173**

## How to Use the Demo

### Step 1: Start Camera
Click **"Start Camera"** button
- Browser will ask for camera permission (allow it)
- Video feed will appear

### Step 2: Watch the Magic
The system automatically:
1. **Captures** video frames via Overshoot Vision SDK
2. **Transforms** observations to structured format via GPT-4o
3. **Routes** through semantic filter (Token Company compression)
4. **Stores** events in Neo4j knowledge graph

### Step 3: Check Results
- Results panel shows the stored event data
- Check browser console for detailed logs
- Backend terminal shows semantic routing decisions

### Step 4: Query the Knowledge Graph

Use the REST API to query memories:

```bash
# Get recent events
curl http://localhost:5000/events/user_001?limit=5

# Search by entity (e.g., "laptop")
curl "http://localhost:5000/search/entity/user_001?name=laptop&limit=5"

# Search by place
curl "http://localhost:5000/search/place/user_001?place=office&limit=5"

# Get user routines
curl http://localhost:5000/routines/user_001?limit=10

# Ask questions
curl -X POST http://localhost:5000/qa/user_001 \
  -H "Content-Type: application/json" \
  -d '{"question": "when did I last eat?"}'
```

## Pipeline Flow Explained

### 1. Overshoot Vision Processing
```javascript
// Captures video and generates detailed observations
RealtimeVision → "Person with long dark hair, white jacket,
                  examining Monster energy drink, indoor setting"
```

### 2. GPT-4o Transformation
```javascript
// Structures the observation
{
  "vision": {
    "objects": ["person", "Monster energy drink"],
    "approx_model": "person",
    "color": "black, white"
  },
  "context": {
    "location_type": "indoor",
    "interaction_duration_sec": 2
  }
}
```

### 3. Semantic Routing (Token Company)
```python
# Calculates relevance to care plan concepts
relevance_score = 0.15  # Low relevance to health monitoring

# Applies dynamic compression (high aggressiveness for irrelevant data)
aggressiveness = 0.85  # Compress heavily

# Compressed result saved to graph
```

### 4. Neo4j Storage
```cypher
// Creates knowledge graph nodes and relationships
(User)-[:HAD_EVENT]->(Event)-[:INVOLVES]->(Entity)
(User)-[:HAS_TASK]->(Task)
(Routine {activity, hour, place, count})
```

## Endpoints Reference

### POST /overshoot_event
Store observation from Overshoot SDK
```json
{
  "user_id": "user_001",
  "timestamp": "2024-01-18T10:30:00Z",
  "vision": {...},
  "audio": {...},
  "context": {...}
}
```

### GET /events/:user_id
Get recent events for user

### GET /search/entity/:user_id?name=X
Search events by entity name

### GET /search/place/:user_id?place=X
Search events by place

### GET /routines/:user_id
Get learned routines (activity patterns by hour/place)

### POST /qa/:user_id
Ask natural language questions:
- "when did I last eat?"
- "did I take my medicine today?"
- "give me a summary of today"

## Troubleshooting

### Backend won't start
```bash
# Check if port 5000 is already in use
lsof -i :5000
kill -9 <PID>

# Verify Python dependencies
pip list | grep -E "flask|neo4j|tokenc"
```

### Frontend won't connect
```bash
# Check if backend is running
curl http://localhost:5000/health

# Should return: {"status": "ok", "timestamp": "..."}
```

### Camera not working
- **Chrome:** Settings → Privacy → Camera → Allow for localhost
- **Firefox:** Preferences → Privacy → Permissions → Camera
- Make sure no other app is using the camera

### Neo4j connection errors
```bash
# Verify credentials in backend/.env
cat backend/.env | grep NEO4J

# Test connection
python -c "from neo4j import GraphDatabase; \
  driver = GraphDatabase.driver('neo4j+s://...', auth=('neo4j', 'password')); \
  driver.verify_connectivity(); print('✓ Connected')"
```

## Demo Tips 🎯

### For Best Results:
1. **Good lighting** - helps Overshoot Vision capture details
2. **Clear actions** - pick up objects, read text, move around
3. **Speak naturally** - mention what you're doing
4. **Interact with objects** - the system tracks object states

### What to Show Judges:
1. **Real-time capture** - show video being processed
2. **Knowledge graph** - query recent memories via API
3. **Semantic routing** - show logs of compression decisions
4. **Pattern learning** - show routines being detected
5. **Proactive queries** - ask about past activities

## Architecture Highlights for Judges

### 1. **Multimodal Understanding**
- Combines vision (Overshoot) + text (GPT-4o)
- Tracks objects, people, places, actions

### 2. **Intelligent Storage**
- Semantic router filters noise vs. signal
- Dynamic compression (Token Company API)
- Only stores relevant memories

### 3. **Graph-Based Memory**
- Neo4j knowledge graph
- Entities, relationships, temporal patterns
- Supports complex queries

### 4. **Pattern Recognition**
- Learns routines (activity × hour × place)
- Tracks entity interactions
- Can answer "when did I last..." questions

## System Requirements

- **Python 3.11+**
- **Node.js 18+**
- **Modern browser** (Chrome/Firefox recommended)
- **Webcam**
- **Internet connection** (for APIs)

## API Keys Required

All keys are already configured in the codebase:
- ✅ Overshoot Vision API
- ✅ OpenAI GPT-4o API
- ✅ Token Company API
- ✅ Neo4j Aura credentials

---

**Ready to demo!** 🚀

Start backend → Start frontend → Click "Start Camera" → Watch the magic happen!
