"""
Unified multimodal processor that combines visual and speech context.
Sends frame + transcripts together to GPT-4o for joint understanding.
"""
from __future__ import annotations
import base64
import cv2
from tenacity import retry, stop_after_attempt, wait_exponential
from models import UnifiedObservation
from llm_clients import get_openai_client
from audio_listener import TranscriptEntry


def frame_to_data_url(frame_bgr, jpeg_quality: int = 85) -> str:
    """Convert OpenCV BGR frame to base64 data URL."""
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
    ok, jpg = cv2.imencode(".jpg", frame_bgr, encode_params)
    if not ok:
        raise RuntimeError("Failed to JPEG-encode frame")
    b64 = base64.b64encode(jpg.tobytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=6))
def process_unified(
    frame_bgr,
    transcripts: list[TranscriptEntry],
) -> UnifiedObservation:
    """
    Process a video frame and speech transcripts together for unified understanding.

    Args:
        frame_bgr: OpenCV frame in BGR format
        transcripts: List of speech transcripts from the time window

    Returns:
        UnifiedObservation with combined visual + speech understanding
    """
    image_url = frame_to_data_url(frame_bgr)

    # Combine transcripts into speech context
    speech_text = ""
    if transcripts:
        speech_text = " ".join([t.text for t in transcripts])
        print(f"[UNIFIED] 🎤 Speech context: \"{speech_text[:100]}{'...' if len(speech_text) > 100 else ''}\"")

    # Build the prompt
    prompt = build_unified_prompt(speech_text if speech_text else None)

    print(f"[UNIFIED] 🧠 Processing frame + speech with GPT-4o...")

    response = get_openai_client().chat.completions.parse(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }],
        response_format=UnifiedObservation,
    )

    message = response.choices[0].message
    if message.parsed:
        obs = message.parsed
        print(f"[UNIFIED] 👁️  Activity: {obs.activity}")
        print(f"[UNIFIED]    Place: {obs.place or 'unknown'}")
        print(f"[UNIFIED]    Visual: {obs.visual_summary}")
        if obs.speech_summary:
            print(f"[UNIFIED]    Speech: {obs.speech_summary}")
        if obs.speaker_intent:
            print(f"[UNIFIED]    Intent: {obs.speaker_intent}")
        print(f"[UNIFIED]    Combined: {obs.combined_context}")
        if obs.memories_to_store:
            print(f"[UNIFIED] 💾 Memories to store: {len(obs.memories_to_store)}")
            for m in obs.memories_to_store:
                print(f"[UNIFIED]    - [{m.importance}] {m.summary}")
        if obs.tasks_to_add:
            print(f"[UNIFIED] 📋 Tasks detected: {len(obs.tasks_to_add)}")
            for t in obs.tasks_to_add:
                print(f"[UNIFIED]    - {t.title}")
        print(f"[UNIFIED]    Salience: {obs.salience:.2f}")
        return obs

    raise RuntimeError(f"Model refused or failed to parse: {message.refusal}")


def build_unified_prompt(speech_text: str | None) -> str:
    """Build the prompt for unified multimodal understanding."""

    speech_section = ""
    if speech_text:
        speech_section = f"""

## Speech Context
The user or someone nearby said: "{speech_text}"

When analyzing, consider:
- How does the speech relate to what's visible?
- Is the user referring to something in the scene?
- Are there any commitments, plans, or tasks mentioned?
- Should anything be remembered for later?
"""

    return f"""You are a personal "second brain" assistant analyzing a moment from a user's wearable camera.
Your job is to understand BOTH what the user sees AND what they/others are saying, combining them for full context.

## CRITICAL: Read All Visible Text
**You MUST carefully read and extract any visible text in the image:**
- Book titles, author names, page numbers
- Product labels, brand names, logos (e.g., "Monster Energy", "Red Bull", "Celsius")
- Screen content, app names, notifications
- Signs, labels, receipts, documents
- Any text the user might be referring to when they speak

If the user says "this book" or "this drink", you MUST identify the SPECIFIC title/brand visible in the image.

## Your Task
1. **Read all visible text**: Extract book titles, brands, labels, screen content, page numbers
2. **Understand the scene**: What's happening visually?
3. **Understand the speech** (if any): What's being said and what does it mean?
4. **Combine context**: Link speech references ("this", "that") to specific visible objects
5. **Extract actionable items**:
   - **Memories**: Important facts WITH SPECIFIC NAMES (not "a book" but "The Great Gatsby page 47")
   - **Tasks**: Things the user needs to do WITH SPECIFIC DETAILS

## What to Remember (memories_to_store)
STORE if the speech/visual contains:
- Specific facts, names, dates, numbers
- Commitments or promises ("I'll do X", "remind me to Y")
- Important decisions or conclusions
- References to objects that should be tracked (e.g., "this book", "that document")
- Information about people or places

IGNORE:
- Generic observations without specific value
- Filler words or incomplete thoughts
- Already obvious information

**For each memory, populate `related_entities` with the names of people, objects, or places the memory is about.**
Example: Memory "Met John at Starbucks, he works at Google" → related_entities: ["John", "Starbucks", "Google"]

## What to Track as Tasks (tasks_to_add)
Add a task if:
- User explicitly says they need to do something
- User implies a future action ("I should...", "need to...", "want to...")
- There's a clear commitment or deadline

**IMPORTANT: Task titles must be SPECIFIC and ACTIONABLE:**
- Include specific names, titles, or identifiers visible in the scene
- BAD: "Continue reading book"
- GOOD: "Continue reading 'The Great Gatsby' from page 142"
- BAD: "Call person back"
- GOOD: "Call John about the project proposal"
- BAD: "Buy groceries"
- GOOD: "Buy milk, eggs, and bread from Trader Joe's"

If you can see text (book title, document name, screen content) or hear names, INCLUDE them in the task title.
Use place_hint to note WHERE the task should be done if relevant.

**For each task, populate `related_entities` with the names of people, objects, or places involved.**
Example: Task "Call John about the proposal" → related_entities: ["John"]
Example: Task "Buy milk from Trader Joe's" → related_entities: ["Trader Joe's", "milk"]
{speech_section}

Analyze this frame{' and speech' if speech_text else ''} and provide a unified understanding."""
