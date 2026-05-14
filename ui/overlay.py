from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class Overlay(QWidget):
    """Small always-on-top window for live damage stats."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Damage Analyzer")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.total_label = QLabel("Total Damage: 0")
        self.dps_label = QLabel("DPS: 0.0")

        title_font = QFont("Segoe UI", 13, QFont.Weight.DemiBold)
        value_font = QFont("Segoe UI", 12)
        self.total_label.setFont(title_font)
        self.dps_label.setFont(value_font)

        for label in (self.total_label, self.dps_label):
            label.setStyleSheet("color: #f4f7fb; background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)
        layout.addWidget(self.total_label)
        layout.addWidget(self.dps_label)

        self.setStyleSheet(
            """
            Overlay {
                background-color: rgba(20, 24, 31, 178);
                border: 1px solid rgba(255, 255, 255, 55);
                border-radius: 8px;
            }
            """
        )
        self.resize(240, 86)
        self.move(40, 40)

    def update_stats(self, stats: dict) -> None:
        total_damage = int(stats.get("total_damage", 0))
        dps = float(stats.get("dps", 0.0))

        self.total_label.setText(f"Total Damage: {total_damage:,}")
        self.dps_label.setText(f"DPS: {dps:,.1f}")
