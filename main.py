"""
Second Brain - Unified multimodal processing pipeline.

Processes video frames and speech together for joint understanding.
"""
from __future__ import annotations
import os
import time
import cv2
from datetime import datetime, timezone
from dotenv import load_dotenv

from unified_processor import process_unified
from graph_store import GraphStore, Neo4jConfig
from proactive_agent import maybe_make_suggestion
from audio_listener import AudioListener


def main():
    load_dotenv()

    user_id = os.environ["USER_ID"]
    video_url = os.environ["VIDEO_URL"]

    print("=" * 60)
    print("🧠 SECOND BRAIN - Unified Multimodal Pipeline")
    print("=" * 60)
    print(f"[INIT] User ID: {user_id}")
    print(f"[INIT] Video source: {video_url}")

    # Convert to int if numeric (webcam index)
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

    # Timing configuration
    PROCESS_EVERY_S = 4.0  # Unified processing interval
    SUGGEST_EVERY_S = 8.0  # Proactive suggestion interval

    last_process = 0.0
    last_suggest = 0.0

    # State tracking
    current_place = None
    current_entities = []

    # Start audio listener (buffers transcripts)
    print("[INIT] Starting audio listener...")
    audio = AudioListener()
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

            # === UNIFIED PROCESSING (every 4 seconds) ===
            if now - last_process >= PROCESS_EVERY_S:
                last_process = now

                print(f"\n{'─' * 50}")
                print(f"[BATCH] 📦 Processing time window...")

                # Resize frame (higher res for text readability)
                frame_small = cv2.resize(frame, (1280, 720))

                # Get buffered transcripts
                transcripts = []
                if audio:
                    transcripts = audio.get_and_clear_all_transcripts()
                    if transcripts:
                        print(f"[BATCH] 🎤 {len(transcripts)} speech segment(s) in window")

                try:
                    # Unified multimodal processing
                    obs = process_unified(frame_small, transcripts)
                    ts = datetime.now(timezone.utc)

                    # Update state (always, for proactive agent context)
                    current_place = obs.place or current_place
                    current_entities = [e.name for e in obs.entities]

                    # Only persist interesting events to keep graph clean
                    SALIENCE_THRESHOLD = float(os.environ.get("SALIENCE_THRESHOLD", "0.6"))
                    is_interesting = (
                        obs.salience >= SALIENCE_THRESHOLD
                        or obs.has_actionable_content
                        or obs.memories_to_store
                        or obs.tasks_to_add
                    )

                    if is_interesting:
                        result = gs.upsert_unified_observation(user_id, obs, ts)
                        print(f"[BATCH] ✅ Stored event: {result['event_id'][:8]}... (salience: {obs.salience:.2f})")

                        if result["memory_ids"]:
                            print(f"[BATCH] 💾 Stored {len(result['memory_ids'])} memories")
                        if result["task_ids"]:
                            print(f"[BATCH] 📋 Added {len(result['task_ids'])} tasks")
                    else:
                        print(f"[BATCH] ⏭️  Skipped (salience: {obs.salience:.2f}, not actionable)")

                except Exception as e:
                    print(f"[BATCH] ❌ Error: {e}")

            # === PROACTIVE SUGGESTIONS (every 8 seconds) ===
            if now - last_suggest >= SUGGEST_EVERY_S:
                last_suggest = now

                try:
                    # Get context from graph
                    recent = gs.get_recent_events(user_id, n=8)
                    tasks = gs.get_open_tasks(user_id, limit=30)
                    routines = gs.get_top_routines(user_id, limit=8)

                    # Find related memories
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

                    # Get proactive suggestion (uses Cerebras)
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
