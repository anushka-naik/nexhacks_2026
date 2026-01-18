from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal

EntityKind = Literal["PLACE", "PERSON", "OBJECT", "PRODUCT", "BOOK", "APP", "TOPIC"]


class Entity(BaseModel):
    kind: EntityKind
    name: str = Field(description="SPECIFIC name - use brand names, titles, not generic terms. E.g., 'Monster Energy' not 'energy drink', 'The Great Gatsby' not 'book'")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class ExtractedTask(BaseModel):
    """A task extracted from speech or visual context."""
    title: str
    place_hint: str | None = None
    reason: str  # Why this is a task
    related_entities: list[str] = Field(
        default_factory=list,
        description="Names of people, places, or objects this task involves"
    )


class ExtractedMemory(BaseModel):
    """A memory worth storing from the current context."""
    summary: str
    importance: Literal["low", "medium", "high"] = "medium"
    reason: str  # Why this should be remembered
    related_entities: list[str] = Field(
        default_factory=list,
        description="Names of people, places, or objects this memory is about"
    )


class UnifiedObservation(BaseModel):
    """
    Unified observation from both visual and audio context.
    This is the main output of the multimodal processor.
    """
    # Visual context
    activity: str = Field(description="What the user is doing (from video)")
    place: str | None = Field(default=None, description="Where the user is")
    visual_summary: str = Field(description="1-sentence description of the scene")
    entities: list[Entity] = Field(default_factory=list, description="People, products, books, places seen - use SPECIFIC names (brand names, book titles, person names), never generic terms")

    # Speech context
    speech_summary: str | None = Field(default=None, description="Summary of what was said, if anything")
    speaker_intent: str | None = Field(default=None, description="What the speaker seems to want/mean")

    # Combined understanding
    combined_context: str = Field(description="Unified understanding of visual + speech context")

    # Extracted actionable items
    memories_to_store: list[ExtractedMemory] = Field(
        default_factory=list,
        description="Important information to remember from this moment"
    )
    tasks_to_add: list[ExtractedTask] = Field(
        default_factory=list,
        description="Tasks or todos mentioned that should be tracked"
    )

    # Metadata
    salience: float = Field(default=0.5, ge=0.0, le=1.0, description="How important is this moment")
    has_actionable_content: bool = Field(default=False, description="True if memories or tasks were extracted")


# Keep legacy Observation for backwards compatibility
class Observation(BaseModel):
    activity: str
    summary: str
    place: str | None = None
    entities: list[Entity] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    salience: float = Field(default=0.5, ge=0.0, le=1.0)


class Suggestion(BaseModel):
    notify: bool
    type: Literal["REMINDER", "SUGGESTION", "ALERT", "NOTE"] = "SUGGESTION"
    message: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str = ""
    related_task_ids: list[str] = Field(default_factory=list)
