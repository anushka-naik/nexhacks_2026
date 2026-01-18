import asyncio
import contextlib
import json
import logging
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    room_io,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

TODO_SNAPSHOT_INTERVAL_SECONDS = 30.0
MAX_TRANSCRIPT_UTTERANCES = 100


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a silent todo-list assistant. "
                "The user speaks naturally about things they need to do. "
                "Listen carefully and infer concise todo items only when the user is "
                "expressing a task, reminder, or commitment. "
                "Group todos into clear categories like Work, Personal, or Other based "
                "on the content. "
                "Never speak back to the user or ask questions; keep an internal, "
                "well-organized list of todos."
            ),
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


def _looks_like_todo(text: str) -> bool:
    lowered = text.lower()
    trigger_phrases = [
        "i need to",
        "i have to",
        "remind me to",
        "we need to",
        "let's",
        "let us",
        "i should",
        "i must",
        "don't forget to",
    ]
    return any(phrase in lowered for phrase in trigger_phrases)


def _infer_category_name(text: str) -> str:
    lowered = text.lower()
    work_keywords = [
        "email",
        "meeting",
        "deck",
        "slides",
        "project",
        "code",
        "bug",
        "deploy",
        "work",
        "report",
    ]
    personal_keywords = [
        "buy",
        "pickup",
        "pick up",
        "grocery",
        "groceries",
        "mom",
        "dad",
        "friend",
        "flight",
        "travel",
        "birthday",
    ]
    if any(word in lowered for word in work_keywords):
        return "Work"
    if any(word in lowered for word in personal_keywords):
        return "Personal"
    return "Other"


def _build_todo_snapshot(utterances: list[str]) -> dict:
    categories: dict[str, dict] = {}
    for text in utterances:
        if not text:
            continue
        if not _looks_like_todo(text):
            continue
        category_name = _infer_category_name(text)
        key = category_name.lower()
        if key not in categories:
            categories[key] = {
                "id": key,
                "name": category_name,
                "tasks": [],
            }
        categories[key]["tasks"].append(
            {
                "id": str(uuid.uuid4()),
                "text": text,
            }
        )
    return {
        "type": "TODO_SNAPSHOT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": list(categories.values()),
    }


async def _publish_todo_snapshots(ctx: JobContext, utterances: list[str]) -> None:
    while True:
        await asyncio.sleep(TODO_SNAPSHOT_INTERVAL_SECONDS)
        if not utterances:
            continue
        snapshot = _build_todo_snapshot(list(utterances))
        payload = json.dumps(snapshot).encode("utf-8")
        try:
            await ctx.room.local_participant.publish_data(
                payload,
                reliable=True,
                topic="todos",
            )
        except Exception:
            logger.exception("failed to publish todo snapshot")


@server.rtc_session()
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-streaming", language="en"),
        llm=inference.LLM(model="openai/gpt-4.1-mini"),
        tts=inference.TTS(
            model="cartesia/sonic-3",
            voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    utterances: list[str] = []

    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(event) -> None:
        transcript = getattr(event, "transcript", "")
        is_final = getattr(event, "is_final", True)
        if not transcript or not is_final:
            return
        utterances.append(transcript)
        if len(utterances) > MAX_TRANSCRIPT_UTTERANCES:
            del utterances[0 : len(utterances) - MAX_TRANSCRIPT_UTTERANCES]

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
            audio_output=False,
            text_output=False,
        ),
    )

    await ctx.connect()

    shutdown_event = asyncio.Event()

    async def _on_shutdown(reason: str) -> None:
        logger.info("job shutting down: %s", reason)
        shutdown_event.set()

    ctx.add_shutdown_callback(_on_shutdown)

    snapshot_task = asyncio.create_task(_publish_todo_snapshots(ctx, utterances))
    try:
        await shutdown_event.wait()
    finally:
        snapshot_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await snapshot_task


if __name__ == "__main__":
    cli.run_app(server)
