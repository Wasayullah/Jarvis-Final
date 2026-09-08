"""Microphone speech-to-text using sounddevice + Google Speech Recognition.

Streams audio with sounddevice, detects speech start/end by energy level,
and recognises with Google's free API.  Auto-stops after a silence gap.
"""

import threading
import time as _time
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None


class VoiceInput:
    """sounddevice + Google speech recogniser with auto-silence detection."""

    def __init__(self):
        self._recognizer = None
        self._lock = threading.Lock()
        self._stop_flag = False

    def _ensure_recognizer(self):
        if self._recognizer is None:
            if sr is None:
                raise RuntimeError("speech_recognition not installed")
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 3000
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 0.8

    def _find_device(self):
        """Return index of first available input device, or None."""
        default_in = sd.default.device[0]
        if default_in is not None and default_in >= 0:
            dev = sd.query_devices(default_in)
            if dev.get("max_input_channels", 0) > 0:
                return default_in
        for i in range(len(sd.query_devices())):
            dev = sd.query_devices(i)
            if dev.get("max_input_channels", 0) > 0:
                return i
        return None

    # ------------------------------------------------------------- public
    def available(self) -> bool:
        """True if sounddevice + microphone are available."""
        if sd is None:
            return False
        try:
            return self._find_device() is not None
        except Exception:
            return False

    def listen(self, timeout=5.0, _silence_timeout=1.5) -> str:
        """Record audio for a *fixed* number of seconds (*timeout*), then
        recognise whatever was captured.  It does NOT wait for a silence gap —
        the input is taken automatically as soon as the time limit is reached
        (or earlier if the user taps the mic button to stop)."""
        if sr is None:
            raise RuntimeError("speech_recognition not installed")
        if sd is None:
            raise RuntimeError("sounddevice not installed")

        self._ensure_recognizer()
        self._stop_flag = False

        samplerate = 16000
        chunk = 1024
        device = self._find_device()
        if device is None:
            raise RuntimeError("no input device found")

        recorded = bytearray()
        total_samples = 0
        max_samples = int(timeout * samplerate)

        try:
            with sd.InputStream(
                device=device,
                samplerate=samplerate,
                channels=1,
                dtype="int16",
                blocksize=chunk,
            ) as stream:
                while total_samples < max_samples and not self._stop_flag:
                    data, _ = stream.read(chunk)
                    total_samples += chunk
                    recorded.extend(data.tobytes())
        except Exception as e:
            raise RuntimeError(f"recording error: {e}")

        if len(recorded) == 0:
            return ""

        audio_data = sr.AudioData(bytes(recorded), samplerate, 2)

        try:
            text = self._recognizer.recognize_google(audio_data, language="en-US")
            return text.strip() if text else ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            raise RuntimeError(f"google API error: {e}")

    def stop(self):
        """Signal the recording loop to stop immediately."""
        self._stop_flag = True

    def close(self):
        self.stop()
