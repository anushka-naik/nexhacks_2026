from __future__ import annotations
import base64
import cv2
from tenacity import retry, stop_after_attempt, wait_exponential
from models import Observation
from llm_clients import get_openai_client

def frame_to_data_url_bgr(frame_bgr, jpeg_quality: int = 70) -> str:
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
    ok, jpg = cv2.imencode(".jpg", frame_bgr, encode_params)
    if not ok:
        raise RuntimeError("Failed to JPEG-encode frame")
    b64 = base64.b64encode(jpg.tobytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=6))
def extract_observation_from_frame(frame_bgr) -> Observation:
    image_url = frame_to_data_url_bgr(frame_bgr)

    prompt = (
        "You are a wearable-camera scene understanding system for a personal second brain.\n"
        "Given this single egocentric frame, infer:\n"
        "- user's likely activity (short verb phrase)\n"
        "- short factual summary (1 sentence)\n"
        "- place (if guessable; e.g., 'grocery store', 'office', 'kitchen')\n"
        "- salient entities with kind in {PLACE, PERSON, OBJECT, APP, TOPIC}\n"
        "Be conservative; avoid guessing specific identities.\n"
    )

    response = get_openai_client().chat.completions.parse(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }],
        response_format=Observation,
    )

    message = response.choices[0].message
    if message.parsed:
        return message.parsed
    raise RuntimeError(f"Model refused or failed to parse: {message.refusal}")
