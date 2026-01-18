from __future__ import annotations
import io
import threading
import queue
import numpy as np
import sounddevice as sd
from llm_clients import get_openai_client

# Audio settings
SAMPLE_RATE = 16000  # Whisper prefers 16kHz
CHANNELS = 1
CHUNK_DURATION_S = 8  # Transcribe every 8 seconds of audio
SILENCE_THRESHOLD = 0.01  # RMS threshold for silence detection


class AudioListener:
    """Continuously captures audio and transcribes speech using Whisper."""

    def __init__(self, on_transcript: callable):
        """
        Args:
            on_transcript: Callback function(text: str) called when speech is transcribed
        """
        self.on_transcript = on_transcript
        self.audio_queue = queue.Queue()
        self.running = False
        self._thread = None
        self._process_thread = None

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio chunk."""
        if status:
            print(f"[AUDIO] Stream status: {status}")
        # Put a copy of the audio data in the queue
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
                # Get audio chunk with timeout
                chunk = self.audio_queue.get(timeout=0.5)
                chunk_duration = len(chunk) / SAMPLE_RATE

                # Skip if silent
                if self._is_silent(chunk):
                    # If we have buffered audio and hit silence, process it
                    if buffer_duration > 1.0:  # At least 1 second of speech
                        self._transcribe_buffer(buffer, buffer_duration)
                        buffer = []
                        buffer_duration = 0.0
                    continue

                # Add to buffer
                buffer.append(chunk)
                buffer_duration += chunk_duration

                # Process if buffer is full
                if buffer_duration >= CHUNK_DURATION_S:
                    self._transcribe_buffer(buffer, buffer_duration)
                    buffer = []
                    buffer_duration = 0.0

            except queue.Empty:
                # Timeout - check if we have pending audio
                if buffer_duration > 1.0:
                    self._transcribe_buffer(buffer, buffer_duration)
                    buffer = []
                    buffer_duration = 0.0

        print("[AUDIO] 🎙️  Audio processing thread stopped")

    def _transcribe_buffer(self, buffer: list, duration: float):
        """Transcribe buffered audio using Whisper."""
        if not buffer:
            return

        print(f"[AUDIO] 🎤 Transcribing {duration:.1f}s of audio...")

        # Concatenate all chunks
        audio_data = np.concatenate(buffer, axis=0).flatten()

        # Convert to 16-bit PCM WAV format in memory
        audio_int16 = (audio_data * 32767).astype(np.int16)

        # Create WAV file in memory with proper format
        import wave
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(audio_int16.tobytes())

        wav_buffer.seek(0)

        # Create a file-like object with a name attribute
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
                self.on_transcript(text)
            else:
                print("[AUDIO] 🔇 (silence/noise)")

        except Exception as e:
            print(f"[AUDIO] ❌ Transcription error: {e}")

    def start(self):
        """Start listening to audio."""
        if self.running:
            return

        self.running = True

        # Start processing thread
        self._process_thread = threading.Thread(target=self._process_audio, daemon=True)
        self._process_thread.start()

        # Start audio stream
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=np.float32,
            callback=self._audio_callback,
            blocksize=int(SAMPLE_RATE * 0.5),  # 500ms blocks
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
