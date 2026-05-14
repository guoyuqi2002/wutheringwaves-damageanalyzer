from __future__ import annotations

import time
from typing import Any

from config import MOCK_OCR_INTERVAL_SECONDS


class DamageOCR:
    """Damage number detector.

    This first version returns deterministic mock detections so the capture,
    tracking, and UI pipeline can be tested before real OCR is wired in.
    """

    def __init__(self, mock: bool = True) -> None:
        self.mock = mock
        self._last_mock_time = 0.0
        self._mock_value = 12345
        self._active_mock: dict | None = None
        self._active_mock_frames = 0

    def detect(self, frame: Any) -> list[dict]:
        if not self.mock:
            return []

        if self._active_mock_frames > 0 and self._active_mock is not None:
            self._active_mock_frames -= 1
            return [dict(self._active_mock)]

        now = time.monotonic()
        if now - self._last_mock_time < MOCK_OCR_INTERVAL_SECONDS:
            return []

        self._last_mock_time = now
        value = self._mock_value
        self._mock_value += 1111

        self._active_mock = {
            "value": value,
            "box": [120, 160, 96, 34],
            "confidence": 0.95,
        }
        self._active_mock_frames = 2
        return [dict(self._active_mock)]
