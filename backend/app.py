from flask import Flask, request, jsonify
from flask_cors import CORS
from dataclasses import dataclass
from datetime import datetime, timezone
import os
import subprocess
from dotenv import load_dotenv
from graph_store import GraphStore, Neo4jConfig
from models import Observation, Entity
from tokenc import TokenClient, Model
from semantic_router_ttc import SemanticRouter, CARE_PLAN_CONCEPTS, overshoot_event_to_text

# Load environment variables
load_dotenv()

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
semantic_router = None


def _get_token_client():
    global token_client
    if token_client is None:
        api_key = os.environ.get("TOKENC_API_KEY")
        if not api_key:
            return None
        token_client = TokenClient(api_key=api_key)
    return token_client


def _get_semantic_router():
    global semantic_router
    if semantic_router is None:
        semantic_router = SemanticRouter(CARE_PLAN_CONCEPTS, similarity_threshold=0.45)
    return semantic_router


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


def send_imessage_notification(phone: str, message: str):
    """Send iMessage notification using the Node.js script"""
    if not phone:
        return False, "", "Phone number not provided"
        
    # Script is in the project root (parent of backend)
    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "imessage_notify.js")
    
    try:
        # Run the node script
        result = subprocess.run(
            ["node", script_path, phone, message],
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        err = f"Error running iMessage script: {e}"
        print(err)
        return False, "", err


def format_answer_for_imessage(data):
    """Format the QA response data into a short text message"""
    answer_type = data.get("answer_type")
    
    if answer_type == "daily_summary":
        count = data.get("event_count", 0)
        summary = data.get("compressed_context")
        if summary:
            return f"Daily Summary: {summary}"
        return f"You have {count} events recorded today."
        
    elif answer_type == "last_meal":
        found = data.get("found")
        if not found:
            return "No recent meal found."
        event = data.get("event", {})
        summary = event.get("summary", "Unknown meal")
        ts = event.get("ts", "")
        # Try to parse timestamp for better readability
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            time_str = dt.strftime("%I:%M %p")
        except:
            time_str = ts
        return f"Last meal: {summary} at {time_str}"
        
    elif answer_type == "medication_status":
        took_today = data.get("took_today")
        if took_today:
            last_event = data.get("last_event", {})
            summary = last_event.get("summary", "")
            return f"Yes, you took your medication today: {summary}"
        else:
            return "No record of you taking medication today."
            
    return None


@app.route('/demo-imessage', methods=['POST'])
def demo_imessage():
    """Send a demo iMessage to test functionality"""
    try:
        data = request.json or {}
        phone = data.get("phone") or os.environ.get("IMESSAGE_PHONE")
        message = data.get("message", "This is a test message from your Memory Assistant.")
        
        if not phone:
            return jsonify({"error": "Phone number required (in body or IMESSAGE_PHONE env var)"}), 400
            
        success, stdout, stderr = send_imessage_notification(phone, message)
        
        if success:
            return jsonify({
                "success": True,
                "message": "iMessage sent successfully",
                "details": stdout
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to send iMessage",
                "details": stderr
            }), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})

@app.route('/demo/seed', methods=['POST'])
def seed_demo_data():
    """Seed database with demo data for testing queries"""
    try:
        user_id = "user_001"

        # Sample observations
        samples = [
            {
                "activity": "working on laptop",
                "summary": "Person typing on MacBook Pro at office desk",
                "place": "office",
                "salience": 0.6,
                "entities": [
                    {"kind": "object", "name": "MacBook Pro", "confidence": 0.95},
                    {"kind": "object", "name": "coffee mug", "confidence": 0.8}
                ]
            },
            {
                "activity": "eating lunch",
                "summary": "Person eating sandwich and salad in kitchen",
                "place": "kitchen",
                "salience": 0.7,
                "entities": [
                    {"kind": "object", "name": "sandwich", "confidence": 0.9},
                    {"kind": "object", "name": "salad", "confidence": 0.85}
                ]
            },
            {
                "activity": "reading",
                "summary": "Person reading The Great Gatsby book on couch",
                "place": "living room",
                "salience": 0.5,
                "entities": [
                    {"kind": "object", "name": "The Great Gatsby", "confidence": 0.95},
                    {"kind": "object", "name": "couch", "confidence": 0.9}
                ]
            },
            {
                "activity": "drinking water",
                "summary": "Person drinking from Hydro Flask water bottle",
                "place": "office",
                "salience": 0.8,
                "entities": [
                    {"kind": "object", "name": "Hydro Flask", "confidence": 0.9},
                    {"kind": "object", "name": "water", "confidence": 0.95}
                ]
            }
        ]

        event_ids = []
        for sample in samples:
            entities = [
                Entity(
                    kind=e.get('kind', 'object'),
                    name=e.get('name', ''),
                    confidence=e.get('confidence', 0.5)
                )
                for e in sample.get('entities', [])
            ]

            observation = Observation(
                activity=sample['activity'],
                summary=sample['summary'],
                place=sample['place'],
                salience=sample['salience'],
                entities=entities
            )

            timestamp = datetime.now(timezone.utc)
            event_id = graph_store.upsert_observation(user_id, observation, timestamp)
            event_ids.append(event_id)

        return jsonify({
            "success": True,
            "message": f"Seeded {len(event_ids)} demo events",
            "event_ids": event_ids
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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


@app.route('/overshoot_event', methods=['POST'])
def receive_overshoot_event():
    try:
        data = request.json or {}
        user_id = data.get("user_id", "user_default")
        ts_raw = data.get("timestamp")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else datetime.now(timezone.utc)
        except Exception:
            ts = datetime.now(timezone.utc)

        router_event = {
            "user_id": user_id,
            "timestamp": ts.isoformat(),
            "vision": data.get("vision") or {},
            "audio": data.get("audio") or data.get("video") or {},
            "context": data.get("context") or {},
            "memory_details": data.get("memory_details") or {},
        }

        router = _get_semantic_router()
        routed = router.route_event(router_event)
        final_text = routed["final_text"]
        relevance = float(routed["relevance_score"])

        vision = router_event["vision"]
        audio = router_event["audio"]
        context = router_event["context"]

        place = context.get("location_type") or "unknown"
        activity = audio.get("intent") or "unknown activity"

        entities = []
        objects = vision.get("objects") or []
        conf = vision.get("confidence", 0.8)
        for obj in objects:
            entities.append(
                Entity(
                    kind="object",
                    name=obj,
                    confidence=conf,
                )
            )

        observation = Observation(
            activity=activity,
            summary=final_text,
            place=place,
            salience=relevance,
            entities=entities,
        )

        event_id = graph_store.upsert_observation(
            user_id=user_id,
            obs=observation,
            ts=ts,
        )

        # Send iMessage notification for the new observation
        phone = os.environ.get("IMESSAGE_PHONE")
        if phone:
            notification_msg = f"New Memory: {final_text}"[:200]
            send_imessage_notification(phone, notification_msg)

        return jsonify({
            "success": True,
            "event_id": event_id,
            "timestamp": ts.isoformat(),
            "semantic_routing": routed,
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
            response = _handle_daily_summary_request(user_id)
            
        elif "last" in text and any(w in text for w in MEAL_KEYWORDS):
            response = _handle_last_meal_request(user_id)
            
        else:
            med_words = ["medicine", "medication", "medecinies", "pill", "pills", "tablet", "tablets", "dose", "insulin", "drug", "drugs"]
            if any(w in text for w in med_words):
                response = _handle_medication_status_request(user_id)
            else:
                return jsonify({"error": "unsupported question pattern"}), 400

        # Attempt to send iMessage with the answer
        if response.status_code == 200:
            try:
                # Extract JSON data from the response
                resp_data = response.get_json()
                msg_text = format_answer_for_imessage(resp_data)
                
                phone = os.environ.get("IMESSAGE_PHONE")
                if phone and msg_text:
                    send_imessage_notification(phone, msg_text)
            except Exception as e:
                print(f"Failed to send iMessage for QA: {e}")
                
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
