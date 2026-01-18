from dataclasses import dataclass

@dataclass
class Entity:
    """Represents an entity (person, object, place) in an observation"""
    kind: str  # "person", "object", "place"
    name: str
    confidence: float

@dataclass
class Observation:
    """Represents a single observation/memory"""
    activity: str
    summary: str
    place: str
    salience: float
    entities: list[Entity]