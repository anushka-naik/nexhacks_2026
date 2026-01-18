# Second Brain - Architecture Overview

## High-Level System Flow

```
┌─────────────┐
│   USER'S    │
│   CAMERA    │  📹 Video Stream
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Browser)                    │
├─────────────────────────────────────────────────────────┤
│  • Captures video via getUserMedia()                    │
│  • Feeds to Overshoot Vision SDK                        │
│  • Receives detailed observations                       │
│  • Transforms via GPT-4o to structured format           │
│  • Sends to Backend API                                 │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP POST /overshoot_event
                          │ JSON payload
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  BACKEND (Flask API)                     │
├─────────────────────────────────────────────────────────┤
│  1. SEMANTIC ROUTER                                     │
│     • Computes relevance to care plan concepts          │
│     • Applies Token Company compression                 │
│     • Dynamic aggressiveness based on relevance         │
│                                                          │
│  2. OBSERVATION PROCESSOR                                │
│     • Extracts entities, activity, place                │
│     • Creates Observation object                        │
│                                                          │
│  3. GRAPH STORAGE                                        │
│     • Stores in Neo4j knowledge graph                   │
│     • Creates nodes: Event, Entity, Routine             │
│     • Updates relationships                             │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 NEO4J KNOWLEDGE GRAPH                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  (User)──────[:HAD_EVENT]──────>(Event)                 │
│                                     │                    │
│                                     │                    │
│                          [:INVOLVES]│                    │
│                                     │                    │
│                                     ▼                    │
│                                 (Entity)                 │
│                             kind: object/person/place    │
│                             name: "laptop"               │
│                             confidence: 0.95             │
│                                                          │
│  (Routine)                                               │
│     activity: "working"                                  │
│     hour: 14                                             │
│     place: "office"                                      │
│     count: 42  ← learns patterns!                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Overshoot Vision SDK

**Purpose:** Real-time video understanding

**Input:** Video frames from webcam

**Output:** Detailed text observations
```
"Person with long dark hair, white jacket, examining
Monster energy drink in indoor setting"
```

**Key Features:**
- Tracks people, objects, actions
- Reads visible text (brands, labels, documents)
- Notes state changes ("bottle opened", "laptop closed")

---

### 2. GPT-4o Transformer

**Purpose:** Structure the observation data

**Input:** Freeform text from Overshoot

**Output:** Structured JSON
```json
{
  "vision": {
    "objects": ["person", "Monster energy drink"],
    "approx_model": "person",
    "color": "black, white",
    "confidence": 0.85
  },
  "audio": {
    "intent": "examining product",
    "keywords": ["Monster"],
    "sentiment": "neutral"
  },
  "context": {
    "location_type": "indoor",
    "interaction_duration_sec": 2
  }
}
```

---

### 3. Semantic Router (Token Company)

**Purpose:** Filter noise, compress irrelevant data

**Process:**
```python
# 1. Compute relevance to care plan
relevance_score = similarity(observation, care_plan_concepts)

# 2. Determine aggressiveness
if relevance_score >= 0.45:
    action = "KEEP RAW"  # Important for care plan
else:
    aggressiveness = calculate(relevance_score)
    compressed = compress(observation, aggressiveness)
    action = "COMPRESSED"
```

**Care Plan Concepts:**
- Drinking water/hydration
- Taking medication
- Falling or injury
- Pain or distress

**Results:**
- High relevance (≥0.45): Stored verbatim
- Low relevance (<0.45): Compressed heavily (saves tokens)

---

### 4. Neo4j Graph Store

**Schema:**

```cypher
// Nodes
(:User {id})
(:Event {id, ts, activity, summary, place, salience})
(:Entity {user_id, kind, name, display_name, confidence})
(:Routine {user_id, activity, hour, place, count})
(:Task {id, user_id, title, status, place_hint})

// Relationships
(User)-[:HAD_EVENT]->(Event)
(Event)-[:INVOLVES {confidence}]->(Entity)
(User)-[:HAS_TASK]->(Task)
```

**Key Queries:**

```cypher
// Find recent events
MATCH (u:User {id: $userId})-[:HAD_EVENT]->(e:Event)
RETURN e ORDER BY e.ts DESC LIMIT 10

// Search by entity
MATCH (u:User {id: $userId})-[:HAD_EVENT]->(e:Event)-[:INVOLVES]->(en:Entity)
WHERE toLower(en.name) CONTAINS toLower($entityName)
RETURN e, collect(en.display_name) as entities

// Find routines (patterns)
MATCH (r:Routine {user_id: $userId})
RETURN r ORDER BY r.count DESC LIMIT 10
```

---

## Data Flow Example

### Scenario: User looking at book

**1. Camera captures frame**
- Video of person holding "The Great Gatsby" book

**2. Overshoot processes**
```
"Person holding book titled 'The Great Gatsby' by F. Scott Fitzgerald,
opened to page 142, in well-lit indoor office setting"
```

**3. GPT-4o structures**
```json
{
  "vision": {
    "objects": ["person", "The Great Gatsby book"],
    "approx_model": "book",
    "color": "blue cover"
  },
  "context": {
    "location_type": "office",
    "interaction_duration_sec": 5
  }
}
```

**4. Semantic Router evaluates**
```python
relevance_score = 0.12  # Not related to care plan
aggressiveness = 0.85   # Compress heavily
final_text = "person with book, office, 5s"
saved_tokens = 18
```

**5. Neo4j stores**
```cypher
CREATE (e:Event {
  id: "abc-123",
  ts: "2024-01-18T10:30:00Z",
  activity: "reading",
  summary: "person with book, office, 5s",
  place: "office",
  salience: 0.12
})

CREATE (en:Entity {
  kind: "object",
  name: "the great gatsby book",
  display_name: "The Great Gatsby book"
})

MERGE (e)-[:INVOLVES]->(en)

// Update routine counter
MERGE (r:Routine {
  user_id: "user_001",
  activity: "reading",
  hour: 10,
  place: "office"
})
SET r.count = r.count + 1
```

---

## API Endpoints

### Storage
- `POST /overshoot_event` - Store new observation
- `POST /observation` - Store generic observation

### Retrieval
- `GET /events/:userId` - Recent events
- `GET /search/entity/:userId?name=X` - Search by entity
- `GET /search/place/:userId?place=X` - Search by location
- `GET /routines/:userId` - Learned patterns
- `GET /entities/:userId` - All known entities

### Intelligence
- `POST /qa/:userId` - Natural language questions
  - "when did I last eat?"
  - "did I take my medicine today?"
  - "give me a summary of today"

### Health
- `GET /health` - System status check

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Vanilla JS + Vite |
| **Vision** | Overshoot SDK |
| **Transform** | OpenAI GPT-4o |
| **Backend** | Python Flask |
| **Compression** | Token Company API |
| **Embeddings** | Sentence Transformers (all-MiniLM-L6-v2) |
| **Database** | Neo4j Aura (cloud) |
| **Hosting** | Local (demo) |

---

## Key Innovation: Dynamic Semantic Routing

Traditional approach:
```
Store everything → Database bloat → Expensive queries
```

Our approach:
```
Relevance check → High relevance? Keep raw
                 ↓
                 Low relevance? Compress heavily
                 ↓
                 Store optimized data → Clean graph
```

**Benefits:**
- 📉 Reduced storage costs
- ⚡ Faster queries
- 🎯 High-quality knowledge graph
- 💰 Token savings on downstream LLM calls

**Example savings:**
- Irrelevant event (person walking by): 85% compression, 18 tokens saved
- Important event (taking medication): 0% compression, full details kept

---

## Future Enhancements

1. **Multimodal Memory Consolidation**
   - Merge similar events across time
   - Create higher-level concepts

2. **Proactive Suggestions**
   - "You usually take medicine at 2pm, haven't seen it yet today"
   - "Based on your routines, time for a water break"

3. **Temporal Reasoning**
   - Answer "How long since I last..." questions
   - Track frequency patterns

4. **Cross-User Insights**
   - Aggregate patterns across users (privacy-preserving)
   - Improve care plan recommendations

---

**Architecture designed for hackathon demo + production scalability** 🚀
