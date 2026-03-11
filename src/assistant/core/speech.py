"""
Speech engine wrapping SpeechRecognition (input) and pyttsx3 (output).

Both engines are initialised lazily and the TTS engine runs on a
dedicated thread to avoid blocking the asyncio event loop.
"""

from __future__ import annotations

import asyncio
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import pyttsx3
import speech_recognition as sr

from assistant.config.settings import AppSettings, VoiceGender
from assistant.utils.logger import get_logger

logger = get_logger(__name__)


class SpeechRecognitionError(Exception):
    """Raised when audio cannot be understood."""


class MicrophoneNotFoundError(Exception):
    """Raised when no microphone device is detected."""


class SpeechEngine:
    """
    Thread-safe wrapper around SpeechRecognition and pyttsx3.

    TTS is dispatched to a single background thread so voice playback
    cannot block the event loop or interleave with recognition.
    """

    def __init__(self, settings: AppSettings) -> None:
        cfg = settings.speech
        self._cfg = cfg
        self._recogniser = sr.Recognizer()
        self._recogniser.energy_threshold = cfg.energy_threshold
        self._recogniser.pause_threshold = cfg.pause_threshold
        self._recogniser.dynamic_energy_threshold = True

        # TTS runs on its own daemon thread
        self._tts_queue: queue.Queue[Optional[str]] = queue.Queue()
        self._tts_thread = threading.Thread(
            target=self._tts_worker, daemon=True, name="tts-worker"
        )
        self._tts_thread.start()

        # Executor for blocking microphone I/O
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mic")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def listen(self) -> str:
        """
        Capture one spoken utterance and return the recognised text.

        Returns:
            Recognised text (lowercased, stripped).

        Raises:
            SpeechRecognitionError: If audio was captured but not understood.
            MicrophoneNotFoundError: If no microphone is available.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._blocking_listen)

    def speak(self, text: str) -> None:
        """Enqueue text for TTS playback (non-blocking)."""
        logger.debug("TTS enqueue: %s", text[:80])
        self._tts_queue.put(text)

    async def speak_async(self, text: str) -> None:
        """Enqueue TTS and await its completion."""
        future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self._tts_queue.put((text, future))
        await future

    def shutdown(self) -> None:
        """Signal the TTS worker to stop and wait for it."""
        self._tts_queue.put(None)  # sentinel
        self._tts_thread.join(timeout=5)
        self._executor.shutdown(wait=False)
        logger.info("SpeechEngine shut down")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _blocking_listen(self) -> str:
        """Blocking microphone capture — runs in a thread pool."""
        try:
            with sr.Microphone() as source:
                logger.debug("Adjusting for ambient noise…")
                self._recogniser.adjust_for_ambient_noise(source, duration=0.5)
                logger.debug("Listening…")
                audio = self._recogniser.listen(
                    source,
                    timeout=self._cfg.recognition_timeout,
                    phrase_time_limit=self._cfg.phrase_time_limit,
                )
        except sr.WaitTimeoutError:
            raise SpeechRecognitionError("No speech detected within timeout.")
        except OSError as exc:
            raise MicrophoneNotFoundError(
                "No microphone found. Check your audio input device."
            ) from exc

        try:
            text = self._recogniser.recognize_google(audio)
            logger.info("Recognised: %s", text)
            return text.lower().strip()
        except sr.UnknownValueError:
            raise SpeechRecognitionError("Could not understand audio.")
        except sr.RequestError as exc:
            raise SpeechRecognitionError(
                f"Speech recognition service unavailable: {exc}"
            ) from exc

    def _tts_worker(self) -> None:
        """Runs in a daemon thread; processes the TTS queue serially."""
        engine = self._build_engine()
        while True:
            item = self._tts_queue.get()
            if item is None:
                break
            if isinstance(item, tuple):
                text, future = item
            else:
                text, future = item, None

            try:
                engine.say(text)
                engine.runAndWait()
            except Exception:
                logger.exception("TTS playback error")
            finally:
                if future and not future.done():
                    future.get_loop().call_soon_threadsafe(future.set_result, None)

    def _build_engine(self) -> pyttsx3.Engine:
        engine = pyttsx3.init()
        engine.setProperty("rate", self._cfg.rate)
        engine.setProperty("volume", self._cfg.volume)

        voices = engine.getProperty("voices")
        if voices:
            gender_filter = "female" if self._cfg.voice_gender == VoiceGender.FEMALE else "male"
            selected = next(
                (v for v in voices if gender_filter in v.name.lower()),
                voices[0],
            )
            engine.setProperty("voice", selected.id)

        return engine
