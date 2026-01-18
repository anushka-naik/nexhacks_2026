# 🚀 Quick Start - Second Brain Demo

## Option 1: Auto-Start (Easiest)

```bash
./start-demo.sh
```

This opens two terminal tabs automatically:
- Backend (Flask API + Neo4j)
- Frontend (Vite dev server)

Then open: **http://localhost:5173**

---

## Option 2: Manual Start (2 Terminals)

### Terminal 1 - Backend:
```bash
cd backend
source .venv/bin/activate
python app.py
```

✅ Backend running at: **http://localhost:5000**

### Terminal 2 - Frontend:
```bash
npm run dev
```

✅ Frontend running at: **http://localhost:5173**

---

## Using the Demo

1. Open **http://localhost:5173** in browser
2. Click **"Start Camera"**
3. Allow camera permissions
4. Point camera at objects/books/products
5. Watch the results panel update in real-time

## What's Happening:

```
Camera → Overshoot Vision → GPT-4o → Semantic Router → Neo4j Graph
```

1. **Overshoot** captures and describes video frames
2. **GPT-4o** structures observations
3. **Semantic Router** filters noise & compresses data
4. **Neo4j** stores as knowledge graph

## Testing the Knowledge Graph Queries

### Option 1: Automated Test Suite
```bash
./test-queries.sh
```
This runs all queries and shows insights!

### Option 2: Manual Testing

**Step 1: Seed demo data**
```bash
curl -X POST http://localhost:5000/demo/seed
```

**Step 2: Run queries**
```bash
# Get recent events
curl http://localhost:5000/events/user_001?limit=5

# Search by entity (e.g., "laptop")
curl "http://localhost:5000/search/entity/user_001?name=laptop"

# Search by place (e.g., "office")
curl "http://localhost:5000/search/place/user_001?place=office"

# Get learned routines
curl http://localhost:5000/routines/user_001

# Ask a question
curl -X POST http://localhost:5000/qa/user_001 \
  -H "Content-Type: application/json" \
  -d '{"question": "when did I last eat?"}'
```

📖 **Full query examples:** See `DEMO_QUERIES.md`

## Troubleshooting

### Backend won't start
```bash
# Make sure venv is activated
cd backend
source .venv/bin/activate
python app.py
```

### Port already in use
```bash
# Kill existing processes
lsof -ti:5000 | xargs kill -9  # Backend
lsof -ti:5173 | xargs kill -9  # Frontend
```

### Camera not working
- Check browser permissions (Settings → Privacy → Camera)
- Close other apps using camera (Zoom, FaceTime, etc.)
- Refresh page and click "Start Camera" again

---

## Demo Flow for Judges

1. **Show Real-time Capture** - Point camera at various objects
2. **Check Console** - Show semantic routing decisions
3. **Query Graph** - Use curl commands to show memories
4. **Show Patterns** - Query routines endpoint
5. **Ask Questions** - Use /qa endpoint

## Files Changed from Prototype

- ✅ Fixed duplicate `app.run()` in `backend/app.py`
- ✅ Added `.env` loading in `backend/app.py`
- ✅ Fixed inconsistent key name in `demo.js` fallback
- ✅ Created startup scripts and documentation

---

**Ready to go!** 🎉

Run `./start-demo.sh` or follow manual steps above.
