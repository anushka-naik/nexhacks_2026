#!/bin/bash

# Frontend Integration Test
# Simulates what the frontend sends to the backend

echo "🧪 Testing Frontend → Backend Integration"
echo "=========================================="
echo ""

BASE_URL="http://localhost:5000"

# Check backend is running
echo -n "Checking backend... "
if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo "✓ Running"
else
    echo "❌ Not running"
    echo "Start backend: cd backend && source .venv/bin/activate && python app.py"
    exit 1
fi

echo ""

# Test the /overshoot_event endpoint (what frontend calls)
echo "Testing /overshoot_event endpoint..."
echo ""

# Simulate frontend payload
PAYLOAD='{
  "user_id": "user_001",
  "timestamp": "2024-01-18T15:30:00Z",
  "vision": {
    "objects": ["laptop", "coffee mug", "notebook"],
    "approx_model": "workspace",
    "color": "silver, white, black",
    "confidence": 0.9
  },
  "video": {
    "intent": "working",
    "keywords": ["laptop", "typing", "work"],
    "sentiment": "focused"
  },
  "context": {
    "location_type": "office",
    "interaction_duration_sec": 5
  }
}'

echo "Payload:"
echo "$PAYLOAD" | jq '.'
echo ""

echo "Sending to backend..."
RESPONSE=$(curl -s -X POST "$BASE_URL/overshoot_event" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo ""
echo "Response:"
echo "$RESPONSE" | jq '.'

# Check if successful
if echo "$RESPONSE" | jq -e '.success' > /dev/null 2>&1; then
    echo ""
    echo "✅ Frontend → Backend integration working!"
    echo ""

    # Verify data was stored
    echo "Verifying stored in graph..."
    EVENT_ID=$(echo "$RESPONSE" | jq -r '.event_id')

    # Check recent events
    RECENT=$(curl -s "$BASE_URL/events/user_001?limit=1")
    if echo "$RECENT" | jq -e '.events[0]' > /dev/null 2>&1; then
        echo "✅ Data successfully stored in Neo4j!"
        echo ""
        echo "Latest event:"
        echo "$RECENT" | jq '.events[0] | {activity, place, summary, entities: ([.entities]? // [])}'
    else
        echo "⚠️  Response successful but couldn't verify storage"
    fi
else
    echo ""
    echo "❌ Integration test failed"
    ERROR=$(echo "$RESPONSE" | jq -r '.error // "Unknown error"')
    echo "Error: $ERROR"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Frontend pipeline verified!"
echo ""
echo "Next steps:"
echo "  1. Start frontend: npm run dev"
echo "  2. Open http://localhost:5173"
echo "  3. Click 'Start Camera'"
echo "  4. Point at objects and watch results"
