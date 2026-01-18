from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal

EntityKind = Literal["PLACE", "PERSON", "OBJECT", "APP", "TOPIC"]

class Entity(BaseModel):
    kind: EntityKind
    name: str
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)

class Observation(BaseModel):
    # We set ts in code; model can also echo it back if you want
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
