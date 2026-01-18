from __future__ import annotations
from dataclasses import dataclass
from neo4j import GraphDatabase
from datetime import datetime, timezone
import uuid
from models import Observation

@dataclass
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str = "neo4j" 

class GraphStore:
    def __init__(self, cfg: Neo4jConfig):
        self.driver = GraphDatabase.driver(cfg.uri, auth=(cfg.user, cfg.password))
        self.database = cfg.database  # ← STORE THE DATABASE NAME
        print(f"[GraphStore] Using database: {self.database}")

    @staticmethod
    def _node_to_dict(node):
        """Convert Neo4j Node to dictionary for JSON serialization"""
        if node is None:
            return None
        data = dict(node)
        # Preserve the node ID if it exists
        if hasattr(node, 'id'):
            data['_neo4j_id'] = node.id
        return data

    def close(self):
        self.driver.close()

    def ensure_constraints(self):
        cypher = """
        CREATE CONSTRAINT user_id IF NOT EXISTS
        FOR (u:User) REQUIRE u.id IS UNIQUE;

        CREATE CONSTRAINT event_id IF NOT EXISTS
        FOR (e:Event) REQUIRE e.id IS UNIQUE;

        CREATE CONSTRAINT task_id IF NOT EXISTS
        FOR (t:Task) REQUIRE t.id IS UNIQUE;

        CREATE INDEX entity_lookup IF NOT EXISTS
        FOR (en:Entity) ON (en.user_id, en.kind, en.name);

        CREATE INDEX routine_lookup IF NOT EXISTS
        FOR (r:Routine) ON (r.user_id, r.activity, r.hour, r.place);
        """
        with self.driver.session(database=self.database) as s:  # ← USE DATABASE
            for stmt in [x.strip() for x in cypher.split(";") if x.strip()]:
                s.run(stmt)

    def upsert_observation(self, user_id: str, obs: Observation, ts: datetime) -> str:
        event_id = str(uuid.uuid4())
        ts_iso = ts.replace(tzinfo=timezone.utc).isoformat()
        hour = ts.astimezone(timezone.utc).hour

        entities_payload = [
            {
                "kind": e.kind,
                "name": e.name.strip().lower(),
                "display_name": e.name.strip(),
                "confidence": float(e.confidence),
            }
            for e in obs.entities
            if e.name and e.kind
        ]

        with self.driver.session(database=self.database) as s:  # ← USE DATABASE
            # Use explicit transaction to ensure commit
            tx = s.begin_transaction()
            try:
                result = tx.run(
                    """
                    MERGE (u:User {id: $user_id})

                    CREATE (ev:Event {
                        id: $event_id,
                        user_id: $user_id,
                        ts: $ts,
                        activity: $activity,
                        summary: $summary,
                        place: $place,
                        salience: $salience
                    })

                    MERGE (u)-[:HAD_EVENT]->(ev)

                    WITH ev
                    UNWIND $entities AS ent
                      MERGE (en:Entity {user_id: $user_id, kind: ent.kind, name: ent.name})
                      ON CREATE SET en.display_name = ent.display_name
                      SET en.last_seen_ts = $ts
                      MERGE (ev)-[:INVOLVES {confidence: ent.confidence}]->(en)

                    // Update a simple routine counter (cheap "learning")
                    WITH ev
                    MERGE (r:Routine {
                        user_id: $user_id,
                        activity: $activity,
                        hour: $hour,
                        place: coalesce($place, "unknown")
                    })
                    SET r.count = coalesce(r.count, 0) + 1,
                        r.last_seen_ts = $ts
                    
                    RETURN ev.id as created_event_id
                    """,
                    user_id=user_id,
                    event_id=event_id,
                    ts=ts_iso,
                    hour=hour,
                    activity=obs.activity,
                    summary=obs.summary,
                    place=obs.place,
                    salience=float(obs.salience),
                    entities=entities_payload,
                )
                
                # Get result
                record = result.single()
                
                # Debug: Check what was created
                summary = result.consume()
                print(f"[GraphStore] Nodes created: {summary.counters.nodes_created}, "
                      f"Relationships: {summary.counters.relationships_created}")
                print(f"[GraphStore] Properties set: {summary.counters.properties_set}")
                
                # Explicitly commit
                tx.commit()
                print(f"[GraphStore] ✅ Transaction committed successfully")
                
            except Exception as e:
                print(f"[GraphStore] ❌ Error during transaction: {e}")
                tx.rollback()
                print(f"[GraphStore] Transaction rolled back")
                raise
                
        return event_id

    def add_task(self, user_id: str, title: str, place_hint: str | None = None) -> str:
        task_id = str(uuid.uuid4())
        ts_iso = datetime.now(timezone.utc).isoformat()
        with self.driver.session(database=self.database) as s:  # ← USE DATABASE
            s.run(
                """
                MERGE (u:User {id: $user_id})
                CREATE (t:Task {
                    id: $task_id,
                    user_id: $user_id,
                    title: $title,
                    status: "OPEN",
                    place_hint: $place_hint,
                    created_ts: $created_ts
                })
                MERGE (u)-[:HAS_TASK]->(t)
                """,
                user_id=user_id,
                task_id=task_id,
                title=title,
                place_hint=place_hint,
                created_ts=ts_iso,
            )
        return task_id

    def get_recent_events(self, user_id: str, n: int = 10) -> list[dict]:
        with self.driver.session(database=self.database) as s:  # ← USE DATABASE
            res = s.run(
                """
                MATCH (:User {id:$user_id})-[:HAD_EVENT]->(e:Event)
                RETURN e
                ORDER BY e.ts DESC
                LIMIT $n
                """,
                user_id=user_id,
                n=n,
            )
            return [self._node_to_dict(r["e"]) for r in res]

    def get_open_tasks(self, user_id: str, limit: int = 20) -> list[dict]:
        with self.driver.session(database=self.database) as s:  # ← USE DATABASE
            res = s.run(
                """
                MATCH (:User {id:$user_id})-[:HAS_TASK]->(t:Task {status:"OPEN"})
                RETURN t
                ORDER BY t.created_ts DESC
                LIMIT $limit
                """,
                user_id=user_id,
                limit=limit,
            )
            return [self._node_to_dict(r["t"]) for r in res]

    def get_top_routines(self, user_id: str, limit: int = 10) -> list[dict]:
        with self.driver.session(database=self.database) as s:  # ← USE DATABASE
            res = s.run(
                """
                MATCH (r:Routine {user_id:$user_id})
                RETURN r
                ORDER BY r.count DESC
                LIMIT $limit
                """,
                user_id=user_id,
                limit=limit,
            )
            return [self._node_to_dict(r["r"]) for r in res]

    def search_memories_by_entity(self, user_id: str, entity_name: str, limit: int = 10) -> list[dict]:
        """Find events that involve a specific entity (person, place, object, topic)."""
        with self.driver.session(database=self.database) as s:  # ← USE DATABASE
            res = s.run(
                """
                MATCH (:User {id:$user_id})-[:HAD_EVENT]->(e:Event)-[:INVOLVES]->(en:Entity)
                WHERE toLower(en.name) CONTAINS toLower($entity_name)
                   OR toLower(en.display_name) CONTAINS toLower($entity_name)
                RETURN e, collect(en.display_name) as entities
                ORDER BY e.ts DESC
                LIMIT $limit
                """,
                user_id=user_id,
                entity_name=entity_name,
                limit=limit,
            )
            return [{"event": self._node_to_dict(r["e"]), "entities": r["entities"]} for r in res]

    def search_memories_by_place(self, user_id: str, place: str, limit: int = 10) -> list[dict]:
        """Find events that occurred at a specific place."""
        with self.driver.session(database=self.database) as s:  # ← USE DATABASE
            res = s.run(
                """
                MATCH (:User {id:$user_id})-[:HAD_EVENT]->(e:Event)
                WHERE e.place IS NOT NULL
                  AND toLower(e.place) CONTAINS toLower($place)
                RETURN e
                ORDER BY e.ts DESC
                LIMIT $limit
                """,
                user_id=user_id,
                place=place,
                limit=limit,
            )
            return [self._node_to_dict(r["e"]) for r in res]

    def search_memories_by_keywords(self, user_id: str, keywords: list[str], limit: int = 10) -> list[dict]:
        """Find events whose summary contains any of the keywords."""
        with self.driver.session(database=self.database) as s:  # ← USE DATABASE
            res = s.run(
                """
                MATCH (:User {id:$user_id})-[:HAD_EVENT]->(e:Event)
                WHERE any(kw IN $keywords WHERE toLower(e.summary) CONTAINS toLower(kw))
                   OR any(kw IN $keywords WHERE toLower(e.activity) CONTAINS toLower(kw))
                RETURN e
                ORDER BY e.salience DESC, e.ts DESC
                LIMIT $limit
                """,
                user_id=user_id,
                keywords=keywords,
                limit=limit,
            )
            return [self._node_to_dict(r["e"]) for r in res]

    def get_all_entities(self, user_id: str, kind: str | None = None, limit: int = 50) -> list[dict]:
        """Get all known entities, optionally filtered by kind."""
        with self.driver.session(database=self.database) as s:  # ← USE DATABASE
            if kind:
                res = s.run(
                    """
                    MATCH (en:Entity {user_id: $user_id, kind: $kind})
                    RETURN en
                    ORDER BY en.last_seen_ts DESC
                    LIMIT $limit
                    """,
                    user_id=user_id,
                    kind=kind,
                    limit=limit,
                )
            else:
                res = s.run(
                    """
                    MATCH (en:Entity {user_id: $user_id})
                    RETURN en
                    ORDER BY en.last_seen_ts DESC
                    LIMIT $limit
                    """,
                    user_id=user_id,
                    limit=limit,
                )
            return [self._node_to_dict(r["en"]) for r in res]

    def find_related_memories(self, user_id: str, current_entities: list[str], current_place: str | None, limit: int = 5) -> list[dict]:
        """
        Find past memories related to current context.
        Used for proactive recall - surfacing relevant past events.
        """
        with self.driver.session(database=self.database) as s:  # ← USE DATABASE
            # Search for events that share entities with current context
            entity_results = []
            if current_entities:
                res = s.run(
                    """
                    MATCH (:User {id:$user_id})-[:HAD_EVENT]->(e:Event)-[:INVOLVES]->(en:Entity)
                    WHERE any(name IN $entity_names WHERE toLower(en.name) CONTAINS toLower(name))
                    WITH e, collect(DISTINCT en.display_name) as matched_entities
                    RETURN e, matched_entities
                    ORDER BY e.salience DESC, e.ts DESC
                    LIMIT $limit
                    """,
                    user_id=user_id,
                    entity_names=current_entities,
                    limit=limit,
                )
                entity_results = [{"event": self._node_to_dict(r["e"]), "matched_on": r["matched_entities"]} for r in res]

            # Search for events at the same place
            place_results = []
            if current_place:
                res = s.run(
                    """
                    MATCH (:User {id:$user_id})-[:HAD_EVENT]->(e:Event)
                    WHERE e.place IS NOT NULL
                      AND toLower(e.place) CONTAINS toLower($place)
                    RETURN e
                    ORDER BY e.salience DESC, e.ts DESC
                    LIMIT $limit
                    """,
                    user_id=user_id,
                    place=current_place,
                    limit=limit,
                )
                place_results = [{"event": self._node_to_dict(r["e"]), "matched_on": ["place: " + current_place]} for r in res]

            # Combine and deduplicate
            seen_ids = set()
            combined = []
            for r in entity_results + place_results:
                event_id = r["event"]["id"]
                if event_id not in seen_ids:
                    seen_ids.add(event_id)
                    combined.append(r)

            return combined[:limit]