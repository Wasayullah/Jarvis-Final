"""Background text-to-speech worker using pyttsx3 on a dedicated thread.

On Windows, pyttsx3's SAPI5 backend only reliably speaks when the engine is
both created and driven (say/runAndWait) on the SAME thread. We therefore
create a fresh engine inside the worker thread for every utterance.
"""

import queue
import re
import threading
import time

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


def _strip_markdown(text: str) -> str:
    """Remove markdown symbols so TTS never reads them aloud."""
    # ``` code fences
    text = re.sub(r"```[\s\S]*?```", "", text)
    # inline `code`
    text = re.sub(r"`([^`]*)`", r"\1", text)
    # bold/italic *** / ** / *
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    # underscore bold/italic
    text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text)
    # strip remaining * and _ so nothing leaks through
    text = text.replace("*", "").replace("_", "")
    # headings  # Title
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # links [text](url) → text
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # images ![alt](url) → alt
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # blockquotes
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    # horizontal rules
    text = re.sub(r"^[-]{3,}\s*$", "", text, flags=re.MULTILINE)
    # list bullets  * item or - item
    text = re.sub(r"^[\s]*[-+]\s+", "", text, flags=re.MULTILINE)
    # numbered lists  1. item
    text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)
    # strikethrough ~~text~~
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    return text.strip()


class Speaker:
    """Runs TTS on a single thread via a queue; never blocks the UI."""

    def __init__(self, on_state_change=None):
        self._on_state_change = on_state_change
        self._queue: "queue.Queue[str]" = queue.Queue()
        self.enabled = self._probe_available()
        self._stop = False
        self._engine = None
        self._engine_lock = threading.Lock()
        self._idle = threading.Event()
        self._idle.set()
        if self.enabled:
            threading.Thread(target=self._worker, daemon=True).start()

    @staticmethod
    def _probe_available() -> bool:
        if pyttsx3 is None:
            return False
        try:
            engine = pyttsx3.init()
            engine.stop()
            return True
        except Exception:
            return False

    def say(self, text: str):
        if self.enabled and text:
            self._queue.put(_strip_markdown(text))

    def wait_until_idle(self, timeout=None):
        """Block until every queued and in-flight utterance finishes speaking."""
        deadline = None if timeout is None else time.time() + timeout
        while not (self._queue.empty() and self._idle.is_set()):
            if deadline is not None:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return self._queue.empty() and self._idle.is_set()
                self._idle.wait(min(0.15, remaining))
            else:
                self._idle.wait(0.15)
        return True

    def stop_speaking(self):
        """Stop current speech immediately without disabling TTS entirely."""
        # Clear the queue to discard pending utterances
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Exception:
                pass
        with self._engine_lock:
            engine = self._engine
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass

    def stop(self):
        self._stop = True
        self.enabled = False
        # Clear the queue to discard pending utterances
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Exception:
                pass
        with self._engine_lock:
            engine = self._engine
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass

    def _worker(self):
        while not self._stop:
            text = self._queue.get()
            if not self.enabled or not text:
                self._idle.set()
                continue
            self._idle.clear()
            if self._on_state_change:
                self._on_state_change("speaking")
            try:
                engine = pyttsx3.init()
                with self._engine_lock:
                    self._engine = engine

                def on_end(name, completed):
                    with self._engine_lock:
                        self._engine = None

                engine.connect("finished-utterance", on_end)
                engine.say(text)
                engine.runAndWait()
                with self._engine_lock:
                    self._engine = None
                engine.stop()
                del engine
            except Exception as e:
                print("TTS ERROR:", e)
                try:
                    with self._engine_lock:
                        self._engine = None
                except Exception:
                    pass
            finally:
                self._idle.set()
            if self._on_state_change:
                self._on_state_change("idle")
