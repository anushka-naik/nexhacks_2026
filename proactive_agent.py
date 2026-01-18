from __future__ import annotations
import json
from datetime import datetime, timezone
from models import Suggestion
from llm_clients import get_cerebras_client, CEREBRAS_MODEL

# JSON Schema for Cerebras structured output (no min/max for numbers)
SUGGESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "notify": {"type": "boolean"},
        "type": {"type": "string", "enum": ["REMINDER", "SUGGESTION", "ALERT", "NOTE"]},
        "message": {"type": "string"},
        "confidence": {"type": "number"},
        "rationale": {"type": "string"},
        "related_task_ids": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["notify", "type", "message", "confidence", "rationale", "related_task_ids"],
    "additionalProperties": False
}


def maybe_make_suggestion(
    user_id: str,
    current_place: str | None,
    tasks: list[dict],
    routines: list[dict],
    recent_events: list[dict],
    related_memories: list[dict] | None = None,
) -> Suggestion:
    """
    Analyze current context and decide whether to proactively notify the user.
    Uses Cerebras for fast inference.

    Args:
        user_id: The user identifier
        current_place: Where the user currently is
        tasks: Open tasks from the graph
        routines: Learned routine patterns
        recent_events: Recent observations
        related_memories: Past memories related to current context (for recall)
    """
    print(f"\n[PROACTIVE] 🧠 Analyzing context with Cerebras ({CEREBRAS_MODEL})...")
    print(f"[PROACTIVE]    📍 Current place: {current_place or 'unknown'}")
    print(f"[PROACTIVE]    📋 Open tasks: {len(tasks)}")
    print(f"[PROACTIVE]    🔄 Known routines: {len(routines)}")
    print(f"[PROACTIVE]    📸 Recent events: {len(recent_events)}")
    print(f"[PROACTIVE]    💭 Related memories: {len(related_memories) if related_memories else 0}")

    # Filter tasks that match current place
    candidate_tasks = []
    if current_place:
        cp = current_place.lower()
        for t in tasks:
            ph = (t.get("place_hint") or "").lower()
            if ph and (ph in cp or cp in ph):
                candidate_tasks.append(t)
        if candidate_tasks:
            print(f"[PROACTIVE]    ✅ {len(candidate_tasks)} tasks match current location")

    # Build context for LLM
    context = {
        "user_id": user_id,
        "current_place": current_place,
        "candidate_tasks": [
            {"id": t["id"], "title": t["title"], "place_hint": t.get("place_hint")}
            for t in candidate_tasks
        ],
        "all_open_tasks": [
            {"id": t["id"], "title": t["title"], "place_hint": t.get("place_hint")}
            for t in tasks[:10]
        ],
        "top_routines": [
            {"activity": r["activity"], "hour": r["hour"], "place": r["place"], "count": r["count"]}
            for r in routines
        ],
        "recent_events": [
            {"ts": e["ts"], "activity": e.get("activity"), "place": e.get("place"), "summary": e.get("summary")}
            for e in recent_events
        ],
        "related_memories": [
            {
                "summary": m["event"].get("summary"),
                "when": m["event"].get("ts"),
                "place": m["event"].get("place"),
                "matched_on": m.get("matched_on", []),
            }
            for m in (related_memories or [])
        ],
        "now_utc": datetime.now(timezone.utc).isoformat(),
        "current_hour": datetime.now().hour,
    }

    instructions = """You are a proactive personal assistant with access to the user's "second brain" - their memories, tasks, and routines.

Your job is to decide whether to notify the user RIGHT NOW with helpful information.

NOTIFY for:
- Tasks that are relevant to the current location or activity
- Past memories that are relevant to what's happening now (e.g., "Last time you were here, you mentioned wanting to buy milk")
- Routine-based reminders (e.g., user usually does X at this time/place)
- Important connections between current context and past events

DO NOT NOTIFY for:
- Generic observations with no actionable insight
- Information the user just experienced (they already know)
- Low-confidence guesses

If you notify, make the message:
- Specific and actionable
- Reference the relevant memory/task/routine
- Brief (1-2 sentences max)

Think step by step:
1. What is the user doing right now?
2. Are there any relevant tasks for this context?
3. Are there any past memories that connect to the current situation?
4. Is this a good time to remind them of something?
5. Would this notification be genuinely helpful?

Respond with valid JSON."""

    print("[PROACTIVE] 🤔 Asking Cerebras to evaluate...")

    try:
        response = get_cerebras_client().chat.completions.create(
            model=CEREBRAS_MODEL,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": f"Context:\n{json.dumps(context, indent=2)}"},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "suggestion",
                    "strict": True,
                    "schema": SUGGESTION_SCHEMA
                }
            }
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        sug = Suggestion(**data)

        if sug.notify:
            print(f"[PROACTIVE] 💡 Decision: NOTIFY ({sug.type})")
            print(f"[PROACTIVE]    Message: {sug.message}")
            print(f"[PROACTIVE]    Rationale: {sug.rationale}")
            print(f"[PROACTIVE]    Confidence: {sug.confidence:.2f}")
        else:
            print(f"[PROACTIVE] 🔇 Decision: Don't notify")
            print(f"[PROACTIVE]    Reason: {sug.rationale}")
        return sug

    except Exception as e:
        print(f"[PROACTIVE] ❌ Error: {e}")

    return Suggestion(notify=False, message="", rationale="Analysis failed")
