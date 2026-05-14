from __future__ import annotations

import sys
import traceback

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from capture.window_capture import WindowCapture
from config import CAPTURE_FPS, DAMAGE_ROI, MOCK_OCR
from detect.damage_ocr import DamageOCR
from track.damage_tracker import DamageTracker
from ui.overlay import Overlay


class DamageAnalyzerApp:
    def __init__(self) -> None:
        self.overlay = Overlay()
        self.capture = WindowCapture(roi=DAMAGE_ROI)
        self.ocr = DamageOCR(mock=MOCK_OCR)
        self.tracker = DamageTracker()
        self.overlay.active_slot_changed.connect(self.tracker.set_active_slot)

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.setInterval(max(1, int(1000 / CAPTURE_FPS)))

    def start(self) -> None:
        self.overlay.show()
        self.timer.start()

    def tick(self) -> None:
        try:
            frame = self.capture.grab()
            detections = self.ocr.detect(frame)
            stats = self.tracker.update(detections)
            self.overlay.update_stats(stats)
        except Exception:
            traceback.print_exc()
            self.timer.stop()

    def close(self) -> None:
        self.capture.close()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Damage Analyzer")
    app.setApplicationDisplayName("Damage Analyzer")
    analyzer = DamageAnalyzerApp()
    app.aboutToQuit.connect(analyzer.close)
    analyzer.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
