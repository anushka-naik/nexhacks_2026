from __future__ import annotations
import os
import time
import cv2
from datetime import datetime, timezone
from dotenv import load_dotenv

from llm_vision import extract_observation_from_frame
from graph_store import GraphStore, Neo4jConfig
from proactive_agent import maybe_make_suggestion
from audio_listener import AudioListener
from speech_analyzer import process_speech_for_memory


def main():
    load_dotenv()

    user_id = os.environ["USER_ID"]
    video_url = os.environ["VIDEO_URL"]

    print("=" * 60)
    print("🧠 SECOND BRAIN - Personal Memory System")
    print("=" * 60)
    print(f"[INIT] User ID: {user_id}")
    print(f"[INIT] Video source: {video_url}")

    # Convert to int if it's a numeric string (for webcam indices)
    try:
        video_url = int(video_url)
    except ValueError:
        pass

    # Initialize graph store
    print("[INIT] Connecting to Neo4j knowledge graph...")
    gs = GraphStore(Neo4jConfig(
        uri=os.environ["NEO4J_URI"],
        user=os.environ["NEO4J_USER"],
        password=os.environ["NEO4J_PASSWORD"],
    ))
    gs.ensure_constraints()
    print("[INIT] ✅ Graph database connected")

    # Initialize video capture
    print(f"[INIT] Opening video stream...")
    cap = cv2.VideoCapture(video_url)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video stream: {video_url}")
    print("[INIT] ✅ Video capture started")

    # State tracking
    sample_every_s = 2.0
    suggest_every_s = 8.0
    last_sample = 0.0
    last_suggest = 0.0
    current_place = None
    current_activity = None
    current_entities = []

    # Audio listener callback
    def on_speech_transcript(text: str):
        """Called when speech is transcribed."""
        print(f"\n[SPEECH] 🎤 Processing transcript...")
        result = process_speech_for_memory(
            user_id=user_id,
            transcript=text,
            graph_store=gs,
            current_place=current_place,
            recent_activity=current_activity,
        )
        if result["stored_memory"]:
            print(f"[SPEECH] 💾 Memory stored: {result['memory_id'][:8]}...")
        if result["stored_task"]:
            print(f"[SPEECH] 📋 Task added: {result['task_id'][:8]}...")

    # Start audio listener
    print("[INIT] Starting audio listener...")
    audio = AudioListener(on_transcript=on_speech_transcript)
    try:
        audio.start()
        print("[INIT] ✅ Audio listener started")
    except Exception as e:
        print(f"[INIT] ⚠️  Audio listener failed: {e}")
        print("[INIT]    Continuing without audio...")
        audio = None

    print("\n" + "=" * 60)
    print("🚀 System running - Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    try:
        while True:
            now = time.time()

            # Read frame
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.2)
                continue

            # === FRAME SAMPLING ===
            if now - last_sample >= sample_every_s:
                last_sample = now

                print(f"\n[VISION] 📷 Analyzing frame...")

                # Resize to reduce tokens/cost
                frame_small = cv2.resize(frame, (640, 360))

                try:
                    obs = extract_observation_from_frame(frame_small)
                    ts = datetime.now(timezone.utc)

                    print(f"[VISION] 👁️  Activity: {obs.activity}")
                    print(f"[VISION]    Place: {obs.place or 'unknown'}")
                    print(f"[VISION]    Summary: {obs.summary}")
                    if obs.entities:
                        entity_names = [e.name for e in obs.entities]
                        print(f"[VISION]    Entities: {', '.join(entity_names)}")
                    print(f"[VISION]    Salience: {obs.salience:.2f}")

                    # Store in graph
                    event_id = gs.upsert_observation(user_id, obs, ts)
                    print(f"[VISION] ✅ Stored as event: {event_id[:8]}...")

                    # Update current state
                    current_place = obs.place or current_place
                    current_activity = obs.activity
                    current_entities = [e.name for e in obs.entities]

                except Exception as e:
                    print(f"[VISION] ❌ Error: {e}")

            # === PROACTIVE SUGGESTIONS ===
            if now - last_suggest >= suggest_every_s:
                last_suggest = now

                try:
                    # Get context from graph
                    recent = gs.get_recent_events(user_id, n=8)
                    tasks = gs.get_open_tasks(user_id, limit=30)
                    routines = gs.get_top_routines(user_id, limit=8)

                    # Find related memories for recall
                    related_memories = []
                    if current_entities or current_place:
                        print(f"[RECALL] 🔍 Searching for related memories...")
                        related_memories = gs.find_related_memories(
                            user_id,
                            current_entities=current_entities,
                            current_place=current_place,
                            limit=5
                        )
                        if related_memories:
                            print(f"[RECALL] 💭 Found {len(related_memories)} related memories")
                            for rm in related_memories[:3]:
                                print(f"[RECALL]    - {rm['event'].get('summary', 'No summary')[:50]}...")

                    # Get proactive suggestion
                    sug = maybe_make_suggestion(
                        user_id,
                        current_place,
                        tasks,
                        routines,
                        recent,
                        related_memories=related_memories,
                    )

                    if sug.notify and sug.message.strip():
                        print("\n" + "=" * 60)
                        print(f"💡 [{sug.type}] {sug.message}")
                        print("=" * 60 + "\n")

                except Exception as e:
                    print(f"[PROACTIVE] ❌ Error: {e}")

            # Keep CPU reasonable
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping...")
    finally:
        if audio:
            audio.stop()
        cap.release()
        gs.close()
        print("[SHUTDOWN] ✅ Cleanup complete")


if __name__ == "__main__":
    main()
