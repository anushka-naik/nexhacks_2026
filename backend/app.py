from flask import Flask, request, jsonify
from flask_cors import CORS
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from graph_store import GraphStore, Neo4jConfig
from models import Observation, Entity
from tokenc import TokenClient, Model

app = Flask(__name__)
CORS(app)  

# Neo4j Configuration
neo4j_config = Neo4jConfig(
    uri="neo4j+s://df6f46e8.databases.neo4j.io",
    user="neo4j",
    password="GrFPX0A9rfqeWZgJY-GNygpTSESYCI8yobmy2QUI_QA"
)

graph_store = GraphStore(neo4j_config)
graph_store.ensure_constraints()


token_client = None


def _get_token_client():
    global token_client
    if token_client is None:
        api_key = os.environ.get("TOKENC_API_KEY")
        if not api_key:
            return None
        token_client = TokenClient(api_key=api_key)
    return token_client


def _node_to_dict(node):
    data = dict(node)
    node_id = node.get("id")
    if node_id is not None:
        data["id"] = node_id
    return data


def _parse_ts(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _events_for_day(user_id, date_obj):
    events = graph_store.get_recent_events(user_id, 200)
    results = []
    for node in events:
        ts = node.get("ts")
        dt = _parse_ts(ts)
        if not dt:
            continue
        if dt.date() == date_obj:
            event = _node_to_dict(node)
            results.append(event)
    results.sort(key=lambda e: e.get("ts", ""))
    return results


MEAL_KEYWORDS = ["meal", "breakfast", "lunch", "dinner", "snack", "food", "eat", "ate", "eating"]
MEDICATION_KEYWORDS = ["medicine", "medication", "pill", "pills", "tablet", "tablets", "dose", "insulin", "drug", "drugs"]

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})

@app.route('/observation', methods=['POST'])
def receive_observation():
    """
    Receive observation from frontend and store in Neo4j
    Expected JSON format:
    {
        "user_id": "user_001",
        "activity": "typing on laptop",
        "summary": "Person working at desk with laptop and coffee",
        "place": "office",
        "salience": 0.8,
        "entities": [
            {"kind": "object", "name": "laptop", "confidence": 0.95},
            {"kind": "object", "name": "coffee", "confidence": 0.9}
        ]
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('user_id'):
            return jsonify({"error": "user_id is required"}), 400
        
        # Create Observation object
        entities = [
            Entity(
                kind=e.get('kind', 'object'),
                name=e.get('name', ''),
                confidence=e.get('confidence', 0.5)
            )
            for e in data.get('entities', [])
        ]
        
        observation = Observation(
            activity=data.get('activity', 'unknown activity'),
            summary=data.get('summary', ''),
            place=data.get('place', 'unknown'),
            salience=data.get('salience', 0.5),
            entities=entities
        )
        
        # Store in Neo4j
        timestamp = datetime.now(timezone.utc)
        event_id = graph_store.upsert_observation(
            user_id=data['user_id'],
            obs=observation,
            ts=timestamp
        )
        
        return jsonify({
            "success": True,
            "event_id": event_id,
            "timestamp": timestamp.isoformat(),
            "message": "Observation stored successfully"
        }), 201
        
    except Exception as e:
        print(f"Error storing observation: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/events/<user_id>', methods=['GET'])
def get_recent_events(user_id):
    """Get recent events for a user"""
    try:
        limit = request.args.get('limit', 10, type=int)
        events = graph_store.get_recent_events(user_id, limit)
        return jsonify({
            "user_id": user_id,
            "events": events,
            "count": len(events)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/search/entity/<user_id>', methods=['GET'])
def search_by_entity(user_id):
    """Search memories by entity name"""
    try:
        entity_name = request.args.get('name', '')
        limit = request.args.get('limit', 10, type=int)
        
        if not entity_name:
            return jsonify({"error": "entity name is required"}), 400
        
        results = graph_store.search_memories_by_entity(user_id, entity_name, limit)
        return jsonify({
            "user_id": user_id,
            "entity": entity_name,
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/search/place/<user_id>', methods=['GET'])
def search_by_place(user_id):
    """Search memories by place"""
    try:
        place = request.args.get('place', '')
        limit = request.args.get('limit', 10, type=int)
        
        if not place:
            return jsonify({"error": "place is required"}), 400
        
        results = graph_store.search_memories_by_place(user_id, place, limit)
        return jsonify({
            "user_id": user_id,
            "place": place,
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/routines/<user_id>', methods=['GET'])
def get_routines(user_id):
    """Get top routines for a user"""
    try:
        limit = request.args.get('limit', 10, type=int)
        routines = graph_store.get_top_routines(user_id, limit)
        return jsonify({
            "user_id": user_id,
            "routines": routines,
            "count": len(routines)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/entities/<user_id>', methods=['GET'])
def get_entities(user_id):
    """Get all entities for a user"""
    try:
        kind = request.args.get('kind', None)
        limit = request.args.get('limit', 50, type=int)
        entities = graph_store.get_all_entities(user_id, kind, limit)
        return jsonify({
            "user_id": user_id,
            "kind": kind,
            "entities": entities,
            "count": len(entities)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _handle_daily_summary_request(user_id):
    today = datetime.now(timezone.utc).date()
    events = _events_for_day(user_id, today)
    raw_lines = []
    for e in events:
        parts = []
        ts = e.get("ts")
        if ts:
            parts.append(f"time: {ts}")
        activity = e.get("activity")
        if activity:
            parts.append(f"activity: {activity}")
        summary = e.get("summary")
        if summary:
            parts.append(f"summary: {summary}")
        place = e.get("place")
        if place:
            parts.append(f"place: {place}")
        salience = e.get("salience")
        if salience is not None:
            parts.append(f"salience: {salience}")
        if parts:
            raw_lines.append("; ".join(parts))
    raw_context = "\n".join(raw_lines)

    compressed_context = None
    tokens_saved = None
    client = _get_token_client()
    if client and raw_context:
        try:
            response = client.compress_input(
                input=raw_context,
                model=Model.BEAR_1,
                aggressiveness=0.6,
            )
            compressed_context = response.output
            tokens_saved = response.tokens_saved
        except Exception:
            compressed_context = None
            tokens_saved = None

    return jsonify({
        "answer_type": "daily_summary",
        "user_id": user_id,
        "date": today.isoformat(),
        "events": events,
        "event_count": len(events),
        "compressed_context": compressed_context,
        "tokens_saved": tokens_saved
    })


def _handle_last_meal_request(user_id):
    nodes = graph_store.search_memories_by_keywords(user_id, MEAL_KEYWORDS, limit=50)
    if not nodes:
        return jsonify({
            "answer_type": "last_meal",
            "user_id": user_id,
            "found": False,
            "event": None
        })

    def sort_key(node):
        dt = _parse_ts(node.get("ts"))
        if not dt:
            return datetime.min.replace(tzinfo=timezone.utc)
        return dt

    last_node = sorted(nodes, key=sort_key, reverse=True)[0]
    event = _node_to_dict(last_node)
    return jsonify({
        "answer_type": "last_meal",
        "user_id": user_id,
        "found": True,
        "event": event
    })


def _handle_medication_status_request(user_id):
    nodes = graph_store.search_memories_by_keywords(user_id, MEDICATION_KEYWORDS, limit=50)
    if not nodes:
        return jsonify({
            "answer_type": "medication_status",
            "user_id": user_id,
            "found": False,
            "last_event": None,
            "took_today": False
        })

    def sort_key(node):
        dt = _parse_ts(node.get("ts"))
        if not dt:
            return datetime.min.replace(tzinfo=timezone.utc)
        return dt

    last_node = sorted(nodes, key=sort_key, reverse=True)[0]
    dt = _parse_ts(last_node.get("ts"))
    today = datetime.now(timezone.utc).date()
    took_today = dt.date() == today if dt else False
    event = _node_to_dict(last_node)

    return jsonify({
        "answer_type": "medication_status",
        "user_id": user_id,
        "found": True,
        "last_event": event,
        "took_today": took_today
    })


@app.route('/qa/<user_id>', methods=['POST'])
def answer_question(user_id):
    try:
        data = request.json or {}
        question = data.get("question", "")
        if not isinstance(question, str) or not question.strip():
            return jsonify({"error": "question is required"}), 400

        text = question.lower()

        if "summary" in text and ("day" in text or "today" in text):
            return _handle_daily_summary_request(user_id)

        if "last" in text and any(w in text for w in MEAL_KEYWORDS):
            return _handle_last_meal_request(user_id)

        med_words = ["medicine", "medication", "medecinies", "pill", "pills", "tablet", "tablets", "dose", "insulin", "drug", "drugs"]
        if any(w in text for w in med_words):
            return _handle_medication_status_request(user_id)

        return jsonify({"error": "unsupported question pattern"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    app.run(debug=True, host='0.0.0.0', port=5000)
    
