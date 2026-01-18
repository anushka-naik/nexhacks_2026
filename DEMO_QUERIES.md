# 🔍 Demo Queries Guide

Your "Second Brain" knowledge graph is queryable! Here's how to show off the insights during your demo.

## Quick Start

### 1. Seed Demo Data
```bash
curl -X POST http://localhost:5000/demo/seed
```

This creates sample events for testing queries.

### 2. Run All Test Queries
```bash
./test-queries.sh
```

This runs a comprehensive test suite showing all query capabilities.

---

## Query Examples for Demo

### 📅 Recent Events
**What you're showing:** Timeline of user's activities

```bash
curl http://localhost:5000/events/user_001?limit=5
```

**Expected output:**
```json
{
  "user_id": "user_001",
  "events": [
    {
      "activity": "drinking water",
      "place": "office",
      "salience": 0.8,
      "summary": "Person drinking from Hydro Flask water bottle",
      "ts": "2024-01-18T15:30:00Z"
    },
    ...
  ],
  "count": 5
}
```

---

### 🔎 Search by Entity
**What you're showing:** Find all memories involving a specific object/person/place

```bash
# Find laptop-related memories
curl "http://localhost:5000/search/entity/user_001?name=laptop"

# Find book-related memories
curl "http://localhost:5000/search/entity/user_001?name=book"

# Find coffee-related memories
curl "http://localhost:5000/search/entity/user_001?name=coffee"
```

**Use case for judges:**
> "Let's say you're looking for your laptop. The system remembers every time it saw it: on the desk, in the bag, in the car..."

---

### 📍 Search by Place
**What you're showing:** Context-aware memory retrieval

```bash
# What happened in the office?
curl "http://localhost:5000/search/place/user_001?place=office"

# What happened in the kitchen?
curl "http://localhost:5000/search/place/user_001?place=kitchen"
```

**Use case for judges:**
> "If you're looking for something and remember 'it was in the kitchen,' the system can show you everything that happened there."

---

### 🔁 Learned Routines
**What you're showing:** Pattern recognition over time

```bash
curl http://localhost:5000/routines/user_001?limit=10
```

**Expected output:**
```json
{
  "routines": [
    {
      "activity": "working on laptop",
      "hour": 14,
      "place": "office",
      "count": 15
    },
    {
      "activity": "drinking water",
      "hour": 10,
      "place": "office",
      "count": 8
    }
  ]
}
```

**Use case for judges:**
> "The system learns patterns. It knows you work at 2pm in the office most days, drink water at 10am. This enables proactive reminders."

---

### 🏷️ All Known Entities
**What you're showing:** The system builds a catalog of everything it's seen

```bash
curl http://localhost:5000/entities/user_001?limit=20
```

**Expected output:**
```json
{
  "entities": [
    {"kind": "object", "name": "MacBook Pro"},
    {"kind": "object", "name": "Hydro Flask"},
    {"kind": "object", "name": "The Great Gatsby"},
    {"kind": "object", "name": "coffee mug"}
  ]
}
```

---

### 💬 Natural Language Questions
**What you're showing:** Query with plain English

```bash
# When did I last eat?
curl -X POST http://localhost:5000/qa/user_001 \
  -H "Content-Type: application/json" \
  -d '{"question": "when did I last eat?"}'

# Did I take my medicine today?
curl -X POST http://localhost:5000/qa/user_001 \
  -H "Content-Type: application/json" \
  -d '{"question": "did I take my medicine?"}'

# Summary of today
curl -X POST http://localhost:5000/qa/user_001 \
  -H "Content-Type: application/json" \
  -d '{"question": "give me a summary of today"}'
```

**Use case for judges:**
> "Instead of complex queries, just ask like you're talking to a person."

---

## Demo Flow for Judges

### Opening
1. Show camera feed capturing real-time
2. Point at 2-3 distinct objects (laptop, book, drink)
3. Let system process for 30 seconds

### Query Demonstrations

**Script:**
> "Now let's query what it remembered..."

**1. Recent events:**
```bash
curl http://localhost:5000/events/user_001?limit=3 | jq '.events[] | {activity, place, summary}'
```
> "Here's the timeline of what just happened."

**2. Search for specific object:**
```bash
curl "http://localhost:5000/search/entity/user_001?name=laptop" | jq '.results[] | {summary: .event.summary, place: .event.place}'
```
> "Let's find every memory involving the laptop."

**3. Show entities catalog:**
```bash
curl http://localhost:5000/entities/user_001 | jq '.entities[] | {kind, name: .display_name}'
```
> "Here's everything the system has learned about - objects, people, places."

**4. Ask a question:**
```bash
curl -X POST http://localhost:5000/qa/user_001 \
  -H "Content-Type: application/json" \
  -d '{"question": "when did I last drink water?"}' | jq '.'
```
> "We can ask questions in natural language."

---

## Advanced Queries (If Time Permits)

### Filter entities by type
```bash
# Just objects
curl "http://localhost:5000/entities/user_001?kind=object"

# Just people
curl "http://localhost:5000/entities/user_001?kind=person"
```

### Combine searches
```bash
# Office + laptop
curl "http://localhost:5000/search/entity/user_001?name=laptop" | \
  jq '.results[] | select(.event.place == "office")'
```

---

## Troubleshooting

### Empty results?
Make sure you've seeded data or captured real events:
```bash
curl -X POST http://localhost:5000/demo/seed
```

### Backend not responding?
Check if it's running:
```bash
curl http://localhost:5000/health
```

### Want pretty JSON?
Pipe through jq:
```bash
curl http://localhost:5000/events/user_001 | jq '.'
```

---

## Key Talking Points for Judges

1. **Real-time Capture**: "Video → Overshoot → GPT-4o → Graph Database (4-second pipeline)"

2. **Intelligent Filtering**: "Semantic router compresses irrelevant data, keeps important stuff verbatim"

3. **Queryable Memory**: "Not just storage - you can search by entity, place, time, or ask questions"

4. **Pattern Learning**: "System learns routines automatically - no programming required"

5. **Proactive Potential**: "With routines, it can remind: 'You usually take medicine at 2pm, haven't seen it yet'"

---

**Saved queries cheat sheet:** Keep `DEMO_QUERIES.md` open during demo!
