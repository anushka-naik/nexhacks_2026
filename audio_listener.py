"""
Audio listener that captures and transcribes speech, buffering results for batch processing.
"""
from __future__ import annotations
import io
import time
import threading
import queue
from dataclasses import dataclass
import numpy as np
import sounddevice as sd
from llm_clients import get_openai_client

# Audio settings
SAMPLE_RATE = 16000  # Whisper prefers 16kHz
CHANNELS = 1
CHUNK_DURATION_S = 4  # Transcribe every 4 seconds of audio
SILENCE_THRESHOLD = 0.01  # RMS threshold for silence detection


@dataclass
class TranscriptEntry:
    """A timestamped transcript from speech."""
    text: str
    timestamp: float  # Unix timestamp when speech was heard


class AudioListener:
    """
    Continuously captures audio and transcribes speech using Whisper.
    Buffers transcripts for retrieval by the main processing loop.
    """

    def __init__(self):
        self.audio_queue = queue.Queue()
        self.transcript_buffer: list[TranscriptEntry] = []
        self.buffer_lock = threading.Lock()
        self.running = False
        self._thread = None
        self._process_thread = None

    def get_recent_transcripts(self, since_timestamp: float) -> list[TranscriptEntry]:
        """
        Get all transcripts since a given timestamp.
        Clears returned transcripts from buffer.
        """
        with self.buffer_lock:
            # Find transcripts after the timestamp
            recent = [t for t in self.transcript_buffer if t.timestamp >= since_timestamp]
            # Keep only future transcripts in buffer
            self.transcript_buffer = [t for t in self.transcript_buffer if t.timestamp >= time.time()]
            return recent

    def get_and_clear_all_transcripts(self) -> list[TranscriptEntry]:
        """Get all buffered transcripts and clear the buffer."""
        with self.buffer_lock:
            transcripts = self.transcript_buffer.copy()
            self.transcript_buffer.clear()
            return transcripts

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio chunk."""
        if status:
            print(f"[AUDIO] Stream status: {status}")
        self.audio_queue.put(indata.copy())

    def _is_silent(self, audio_data: np.ndarray) -> bool:
        """Check if audio chunk is mostly silence."""
        rms = np.sqrt(np.mean(audio_data ** 2))
        return rms < SILENCE_THRESHOLD

    def _process_audio(self):
        """Process audio chunks and transcribe."""
        buffer = []
        buffer_duration = 0.0

        print("[AUDIO] 🎙️  Audio processing thread started")

        while self.running:
            try:
                chunk = self.audio_queue.get(timeout=0.5)
                chunk_duration = len(chunk) / SAMPLE_RATE

                # Skip if silent
                if self._is_silent(chunk):
                    if buffer_duration > 1.0:
                        self._transcribe_buffer(buffer, buffer_duration)
                        buffer = []
                        buffer_duration = 0.0
                    continue

                buffer.append(chunk)
                buffer_duration += chunk_duration

                if buffer_duration >= CHUNK_DURATION_S:
                    self._transcribe_buffer(buffer, buffer_duration)
                    buffer = []
                    buffer_duration = 0.0

            except queue.Empty:
                if buffer_duration > 1.0:
                    self._transcribe_buffer(buffer, buffer_duration)
                    buffer = []
                    buffer_duration = 0.0

        print("[AUDIO] 🎙️  Audio processing thread stopped")

    def _transcribe_buffer(self, buffer: list, duration: float):
        """Transcribe buffered audio using Whisper and add to transcript buffer."""
        if not buffer:
            return

        print(f"[AUDIO] 🎤 Transcribing {duration:.1f}s of audio...")

        audio_data = np.concatenate(buffer, axis=0).flatten()
        audio_int16 = (audio_data * 32767).astype(np.int16)

        import wave
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(2)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(audio_int16.tobytes())

        wav_buffer.seek(0)

        class NamedBytesIO(io.BytesIO):
            name = "audio.wav"

        named_buffer = NamedBytesIO(wav_buffer.read())
        named_buffer.seek(0)

        try:
            transcription = get_openai_client().audio.transcriptions.create(
                model="whisper-1",
                file=named_buffer,
                language="en",
            )

            text = transcription.text.strip()
            if text:
                print(f"[AUDIO] 💬 Heard: \"{text}\"")
                # Add to buffer instead of immediate processing
                entry = TranscriptEntry(text=text, timestamp=time.time())
                with self.buffer_lock:
                    self.transcript_buffer.append(entry)
            else:
                print("[AUDIO] 🔇 (silence/noise)")

        except Exception as e:
            print(f"[AUDIO] ❌ Transcription error: {e}")

    def start(self):
        """Start listening to audio."""
        if self.running:
            return

        self.running = True

        self._process_thread = threading.Thread(target=self._process_audio, daemon=True)
        self._process_thread.start()

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=np.float32,
            callback=self._audio_callback,
            blocksize=int(SAMPLE_RATE * 0.5),
        )
        self._stream.start()
        print("[AUDIO] 🎙️  Started listening to microphone")

    def stop(self):
        """Stop listening."""
        self.running = False
        if hasattr(self, '_stream'):
            self._stream.stop()
            self._stream.close()
        if self._process_thread:
            self._process_thread.join(timeout=2.0)
        print("[AUDIO] 🎙️  Stopped listening")
