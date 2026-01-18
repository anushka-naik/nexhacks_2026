#!/bin/bash

# Test Knowledge Graph Queries
# Demonstrates the "Second Brain" query capabilities

echo "🧠 Testing Second Brain Knowledge Graph Queries"
echo "================================================"
echo ""

BASE_URL="http://localhost:5000"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if backend is running
echo -n "Checking backend health... "
if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo "❌ Backend is not running"
    echo "Start it with: cd backend && source .venv/bin/activate && python app.py"
    exit 1
fi

echo ""

# Seed demo data
echo -e "${BLUE}1. Seeding demo data...${NC}"
curl -s -X POST "$BASE_URL/demo/seed" | jq '.'
echo ""

# Get recent events
echo -e "${BLUE}2. Getting recent events (last 5):${NC}"
curl -s "$BASE_URL/events/user_001?limit=5" | jq '.events[] | {activity, place, salience, summary}'
echo ""

# Search by entity - laptop
echo -e "${BLUE}3. Searching for 'laptop' memories:${NC}"
curl -s "$BASE_URL/search/entity/user_001?name=laptop&limit=5" | jq '.results[] | {activity: .event.activity, place: .event.place, entities}'
echo ""

# Search by entity - book
echo -e "${BLUE}4. Searching for 'book' memories:${NC}"
curl -s "$BASE_URL/search/entity/user_001?name=book&limit=5" | jq '.results[] | {activity: .event.activity, summary: .event.summary, entities}'
echo ""

# Search by place - office
echo -e "${BLUE}5. Searching events in 'office':${NC}"
curl -s "$BASE_URL/search/place/user_001?place=office&limit=5" | jq '.results[] | {activity, summary, salience}'
echo ""

# Get all entities
echo -e "${BLUE}6. Getting all known entities:${NC}"
curl -s "$BASE_URL/entities/user_001?limit=20" | jq '.entities[] | {kind, name: .display_name}'
echo ""

# Get routines
echo -e "${BLUE}7. Getting learned routines:${NC}"
curl -s "$BASE_URL/routines/user_001?limit=10" | jq '.routines[] | {activity, hour, place, count}'
echo ""

# Ask question - last meal
echo -e "${BLUE}8. Asking: 'When did I last eat?'${NC}"
curl -s -X POST "$BASE_URL/qa/user_001" \
  -H "Content-Type: application/json" \
  -d '{"question": "when did I last eat?"}' | jq '.'
echo ""

echo "================================================"
echo -e "${GREEN}✅ All queries completed!${NC}"
echo ""
echo "Try your own queries:"
echo "  curl \"$BASE_URL/search/entity/user_001?name=<entity_name>\""
echo "  curl \"$BASE_URL/search/place/user_001?place=<place_name>\""
echo "  curl -X POST \"$BASE_URL/qa/user_001\" -H 'Content-Type: application/json' -d '{\"question\": \"your question\"}'"
