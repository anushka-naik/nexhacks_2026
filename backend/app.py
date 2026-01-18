from flask import Flask, request, jsonify
from flask_cors import CORS
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from graph_store import GraphStore, Neo4jConfig
from models import Observation, Entity

app = Flask(__name__)
CORS(app)  

# Neo4j Configuration
neo4j_config = Neo4jConfig(
    uri="neo4j+s://df6f46e8.databases.neo4j.io",
    user="neo4j",
    password="GrFPX0A9rfqeWZgJY-GNygpTSESYCI8yobmy2QUI_QA"
)

# Initialize GraphStore
graph_store = GraphStore(neo4j_config)
graph_store.ensure_constraints()

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    