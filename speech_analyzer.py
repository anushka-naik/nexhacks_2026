from __future__ import annotations
import json
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Literal
from graph_store import GraphStore
from models import Observation, Entity
from llm_clients import get_cerebras_client, CEREBRAS_MODEL


class SpeechAnalysis(BaseModel):
    """LLM's analysis of a speech transcript."""
    is_relevant: bool = Field(description="True if this contains information worth remembering")
    relevance_reason: str = Field(description="Brief explanation of why this is/isn't relevant")

    # Memory extraction
    memory_summary: str | None = Field(default=None, description="Key information to remember, if relevant")
    entities_mentioned: list[str] = Field(default_factory=list, description="Names of people, places, or things mentioned")
    topics: list[str] = Field(default_factory=list, description="Topics being discussed")

    # Task detection
    has_task: bool = Field(default=False, description="True if user mentioned something they need to do")
    task_title: str | None = Field(default=None, description="The task to add, if detected")
    task_place_hint: str | None = Field(default=None, description="Location hint for the task, if mentioned")

    # Context
    emotional_tone: str | None = Field(default=None, description="Detected emotional tone (e.g., 'excited', 'stressed', 'casual')")
    conversation_type: Literal["monologue", "dialogue", "ambient", "command"] = Field(
        default="ambient",
        description="Type of speech detected"
    )


# JSON Schema for Cerebras structured output (Cerebras requires anyOf for nullable)
SPEECH_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "is_relevant": {"type": "boolean"},
        "relevance_reason": {"type": "string"},
        "memory_summary": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "entities_mentioned": {"type": "array", "items": {"type": "string"}},
        "topics": {"type": "array", "items": {"type": "string"}},
        "has_task": {"type": "boolean"},
        "task_title": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "task_place_hint": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "emotional_tone": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "conversation_type": {"type": "string", "enum": ["monologue", "dialogue", "ambient", "command"]}
    },
    "required": ["is_relevant", "relevance_reason", "has_task", "conversation_type", "entities_mentioned", "topics"],
    "additionalProperties": False
}


def analyze_speech(transcript: str, recent_context: str | None = None) -> SpeechAnalysis:
    """
    Analyze a speech transcript using Cerebras for fast inference.

    Args:
        transcript: The transcribed speech
        recent_context: Optional context about what's happening (from video)
    """
    print(f"[SPEECH] 🧠 Analyzing transcript with Cerebras ({CEREBRAS_MODEL})...")

    context_prompt = ""
    if recent_context:
        context_prompt = f"\n\nVisual context: {recent_context}"

    prompt = f"""You are a personal memory assistant analyzing speech from a user's wearable device.
Your job is to decide if this speech contains information worth storing in the user's "second brain" memory.

STORE memories for:
- Important facts, names, dates, or numbers mentioned
- Commitments, plans, or things the user needs to do
- Key decisions or conclusions from conversations
- Interesting ideas or insights
- Information about people (relationships, preferences, contact info)
- Places and events discussed

IGNORE:
- Small talk and pleasantries ("how are you", "nice weather")
- Filler words and incomplete sentences
- Background noise or ambient conversation that doesn't involve the user
- Repeated information already captured
- Generic/obvious statements

Transcript: "{transcript}"{context_prompt}

Analyze this transcript and extract any relevant information. Respond with valid JSON."""

    try:
        response = get_cerebras_client().chat.completions.create(
            model=CEREBRAS_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "speech_analysis",
                    "strict": True,
                    "schema": SPEECH_ANALYSIS_SCHEMA
                }
            }
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        analysis = SpeechAnalysis(**data)

        if analysis.is_relevant:
            print(f"[SPEECH] ✅ RELEVANT: {analysis.relevance_reason}")
            if analysis.memory_summary:
                print(f"[SPEECH] 💾 Memory: {analysis.memory_summary}")
            if analysis.has_task:
                print(f"[SPEECH] 📋 Task detected: {analysis.task_title}")
        else:
            print(f"[SPEECH] ⏭️  Ignoring: {analysis.relevance_reason}")
        return analysis

    except Exception as e:
        print(f"[SPEECH] ❌ Analysis error: {e}")

    return SpeechAnalysis(is_relevant=False, relevance_reason="Analysis failed")


def process_speech_for_memory(
    user_id: str,
    transcript: str,
    graph_store: GraphStore,
    current_place: str | None = None,
    recent_activity: str | None = None,
) -> dict:
    """
    Full pipeline: analyze speech, extract memories/tasks, store in graph.

    Returns dict with what was stored.
    """
    result = {
        "stored_memory": False,
        "stored_task": False,
        "memory_id": None,
        "task_id": None,
    }

    # Build context from current state
    context = None
    if current_place or recent_activity:
        context = f"Place: {current_place or 'unknown'}, Activity: {recent_activity or 'unknown'}"

    # Analyze the transcript
    analysis = analyze_speech(transcript, context)

    if not analysis.is_relevant:
        return result

    # Store memory as an observation
    if analysis.memory_summary:
        print(f"[SPEECH] 📝 Storing memory in knowledge graph...")

        # Create entities from the analysis
        entities = []
        for name in analysis.entities_mentioned:
            entities.append(Entity(kind="PERSON", name=name, confidence=0.6))
        for topic in analysis.topics:
            entities.append(Entity(kind="TOPIC", name=topic, confidence=0.7))

        # Create observation from speech
        obs = Observation(
            activity=f"heard: {analysis.conversation_type}",
            summary=analysis.memory_summary,
            place=current_place,
            entities=entities,
            tags=["from_speech"] + analysis.topics,
            salience=0.7 if analysis.has_task else 0.5,
        )

        ts = datetime.now(timezone.utc)
        event_id = graph_store.upsert_observation(user_id, obs, ts)
        result["stored_memory"] = True
        result["memory_id"] = event_id
        print(f"[SPEECH] ✅ Memory stored: {event_id}")

    # Store task if detected
    if analysis.has_task and analysis.task_title:
        print(f"[SPEECH] 📋 Adding task: {analysis.task_title}")
        task_id = graph_store.add_task(
            user_id,
            analysis.task_title,
            analysis.task_place_hint
        )
        result["stored_task"] = True
        result["task_id"] = task_id
        print(f"[SPEECH] ✅ Task added: {task_id}")

    return result
