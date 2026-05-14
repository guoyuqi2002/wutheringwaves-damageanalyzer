from __future__ import annotations

from typing import Optional, Sequence

import cv2
import mss
import numpy as np


class WindowCapture:
    """Screen capture helper backed by mss."""

    def __init__(self, roi: Optional[Sequence[int]] = None) -> None:
        self.roi = roi
        self._sct = mss.mss()

    def grab(self, roi: Optional[Sequence[int]] = None) -> np.ndarray:
        monitor = self._build_monitor(roi or self.roi)
        screenshot = self._sct.grab(monitor)
        frame = np.asarray(screenshot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    def save_frame(self, path: str, roi: Optional[Sequence[int]] = None) -> bool:
        frame = self.grab(roi)
        return bool(cv2.imwrite(path, frame))

    def close(self) -> None:
        self._sct.close()

    def _build_monitor(self, roi: Optional[Sequence[int]]) -> dict:
        if roi is None:
            return self._sct.monitors[0]

        if len(roi) != 4:
            raise ValueError("ROI must be (left, top, width, height)")

        left, top, width, height = [int(value) for value in roi]
        if width <= 0 or height <= 0:
            raise ValueError("ROI width and height must be positive")

        return {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }
