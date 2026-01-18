import json
import os
from typing import Iterable, Dict, Any, List

from sentence_transformers import SentenceTransformer, util
from tokenc import TokenClient, Model


CARE_PLAN_CONCEPTS: List[str] = [
    "drinking water hydration",
    "taking medication pills medicine",
    "falling or injury",
    "pain or distress",
]

SAMPLE_OVERSHOOT_EVENT: Dict[str, Any] = {
    "user_id": "user_default",
    "timestamp": "2023-10-27T10:30:00Z",
    "vision": {
        "objects": ["person with long dark hair"],
        "approx_model": "person",
        "color": "black",
        "confidence": 0.85,
    },
    "audio": {
        "intent": "examining product",
        "keywords": ["Monster"],
        "sentiment": "neutral",
    },
    "context": {
        "location_type": "indoor",
        "interaction_duration_sec": 2,
    },
    "memory_details": {
        "category": "person",
        "specific_attributes": {
            "for_people": (
                "hair: [long, black, straight], facial_features: [none], "
                "clothing: [white jacket, blue shirt], "
                "estimated_age: [20-30], gender: [female]"
            )
        },
        "unique_identifier": "person_long_black_hair_white_jacket_blue_shirt",
    },
}


def overshoot_event_to_text(event: Dict[str, Any]) -> str:
    vision = event.get("vision") or {}
    audio = event.get("audio") or {}
    context = event.get("context") or {}
    memory_details = event.get("memory_details") or {}
    specific_attributes = (memory_details.get("specific_attributes") or {}).get(
        "for_people"
    )

    parts: List[str] = []

    objects = vision.get("objects") or []
    if objects:
        parts.append("objects: " + ", ".join(objects))

    approx_model = vision.get("approx_model")
    if approx_model:
        parts.append(f"approx model: {approx_model}")

    color = vision.get("color")
    if color:
        parts.append(f"color: {color}")

    intent = audio.get("intent")
    if intent:
        parts.append(f"intent: {intent}")

    keywords = audio.get("keywords") or []
    if keywords:
        parts.append("keywords: " + ", ".join(keywords))

    sentiment = audio.get("sentiment")
    if sentiment:
        parts.append(f"sentiment: {sentiment}")

    location_type = context.get("location_type")
    if location_type:
        parts.append(f"location: {location_type}")

    interaction_duration_sec = context.get("interaction_duration_sec")
    if interaction_duration_sec is not None:
        parts.append(f"interaction duration seconds: {interaction_duration_sec}")

    category = memory_details.get("category")
    if category:
        parts.append(f"category: {category}")

    if specific_attributes:
        parts.append(f"attributes: {specific_attributes}")

    if not parts:
        return json.dumps(event, sort_keys=True)

    return ". ".join(parts)


class SemanticRouter:
    def __init__(
        self,
        care_plan_concepts: Iterable[str],
        similarity_threshold: float = 0.45,
    ) -> None:
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.care_plan_concepts = list(care_plan_concepts)
        self.care_plan_embeddings = self.model.encode(
            self.care_plan_concepts, normalize_embeddings=True
        )
        self.similarity_threshold = similarity_threshold

        api_key = os.environ.get("TOKENC_API_KEY")
        if not api_key:
            raise RuntimeError("TOKENC_API_KEY environment variable is not set")
        self.token_client = TokenClient(api_key=api_key)

    def _compute_aggressiveness(self, relevance_score: float) -> float:
        if relevance_score <= 0:
            return 0.9
        if relevance_score >= self.similarity_threshold:
            return 0.3
        ratio = 1.0 - (relevance_score / self.similarity_threshold)
        return 0.3 + 0.6 * ratio

    def route_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = event.get("timestamp", "unknown")
        raw_text = overshoot_event_to_text(event)

        embedding = self.model.encode(raw_text, normalize_embeddings=True)
        scores = util.cos_sim(embedding, self.care_plan_embeddings)[0]
        max_score = float(scores.max())

        if max_score > self.similarity_threshold:
            action = "KEPT RAW"
            final_text = raw_text
            saved_tokens = 0
            aggressiveness = None
        else:
            aggressiveness = self._compute_aggressiveness(max_score)
            response = self.token_client.compress_input(
                input=raw_text,
                model=Model.BEAR_1,
                aggressiveness=aggressiveness,
            )
            action = "COMPRESSED"
            final_text = response.output
            saved_tokens = response.tokens_saved

        log_entry = {
            "timestamp": timestamp,
            "action": action,
            "relevance_score": max_score,
            "final_text": final_text,
            "saved_tokens": saved_tokens,
            "aggressiveness": aggressiveness,
        }

        print(f"[{log_entry['timestamp']}]")
        print(f"[ACTION]: {log_entry['action']}")
        print(f"[RELEVANCE SCORE]: {log_entry['relevance_score']:.4f}")
        print(f"[FINAL TEXT]: {log_entry['final_text']}")
        if log_entry["saved_tokens"] is not None:
            print(f"[SAVED TOKENS]: {log_entry['saved_tokens']}")
        if log_entry["aggressiveness"] is not None:
            print(f"[AGGRESSIVENESS]: {log_entry['aggressiveness']:.2f}")
        print()

        return log_entry

    def run_stream(self, overshoot_stream: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for event in overshoot_stream:
            results.append(self.route_event(event))
        return results


def main() -> None:
    router = SemanticRouter(CARE_PLAN_CONCEPTS, similarity_threshold=0.45)
    router.run_stream([SAMPLE_OVERSHOOT_EVENT])


if __name__ == "__main__":
    main()
