"""
Shared LLM clients for the second brain system.

- OpenAI: Used for vision (image analysis) and audio transcription
- Cerebras: Used for fast text inference (speech analysis, proactive suggestions)
"""
from __future__ import annotations
import os
from openai import OpenAI
from cerebras.cloud.sdk import Cerebras

# Lazy initialization
_openai_client = None
_cerebras_client = None

# Cerebras model for text tasks
CEREBRAS_MODEL = "llama-3.3-70b"


def get_openai_client() -> OpenAI:
    """Get OpenAI client for vision and audio tasks."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI()
        print("[LLM] Initialized OpenAI client (for vision/audio)")
    return _openai_client


def get_cerebras_client() -> Cerebras:
    """Get Cerebras client for fast text inference."""
    global _cerebras_client
    if _cerebras_client is None:
        api_key = os.environ.get("CEREBRAS_API_KEY")
        if not api_key:
            raise ValueError("CEREBRAS_API_KEY environment variable not set")
        _cerebras_client = Cerebras(api_key=api_key)
        print("[LLM] Initialized Cerebras client (for fast text inference)")
    return _cerebras_client
