"""Bounded frame buffer: realtime mode always processes the latest frame."""
from __future__ import annotations

from collections import deque
from threading import Condition


class FrameBuffer:
    def __init__(self, maxsize: int = 8):
        self._buf: deque = deque(maxlen=maxsize)
        self._cond = Condition()
        self.closed = False

    def put_latest(self, item) -> None:
        """Insert, dropping the oldest when full (never grows unbounded)."""
        with self._cond:
            self._buf.append(item)  # deque(maxlen=) drops oldest automatically
            self._cond.notify()

    def get(self, timeout: float = 1.0):
        with self._cond:
            if not self._buf and not self.closed:
                self._cond.wait(timeout)
            if not self._buf:
                return None
            return self._buf.popleft()

    def qsize(self) -> int:
        return len(self._buf)

    def close(self) -> None:
        with self._cond:
            self.closed = True
            self._cond.notify_all()
