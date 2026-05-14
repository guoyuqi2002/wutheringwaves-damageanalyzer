from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


BAR_WIDTH = 220
BAR_HEIGHT = 25
MIN_FILL_WIDTH = 5


class _MetricBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._value = 0.0
        self._max_value = 0.0

        self.setObjectName("metricBarTrack")
        self.setFixedSize(BAR_WIDTH, BAR_HEIGHT)

        self.fill = QLabel(self)
        self.fill.setObjectName("metricBarFill")
        self.fill.setFixedHeight(BAR_HEIGHT)
        self._resize_fill()

    def update_values(self, value: float, max_value: float) -> None:
        self._value = max(0.0, value)
        self._max_value = max(0.0, max_value)
        self._resize_fill()

    def _resize_fill(self) -> None:
        if self._max_value <= 0 or self._value <= 0:
            width = 0
        else:
            width = max(MIN_FILL_WIDTH, int(BAR_WIDTH * self._value / self._max_value))
        self.fill.setFixedWidth(min(BAR_WIDTH, width))


class _SlotDamageRow(QWidget):
    def __init__(self, slot: int) -> None:
        super().__init__()
        self.name_label = QLabel(f"{slot}")
        self.bar = _MetricBar()
        self.damage_label = QLabel("0")
        self.percent_label = QLabel("0.0%")

        self.name_label.setObjectName("slotName")
        self.damage_label.setObjectName("metricValue")
        self.percent_label.setObjectName("percentLabel")
        self.damage_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.addWidget(self.name_label, 0, 0)
        layout.addWidget(self.bar, 0, 1)
        layout.addWidget(self.damage_label, 0, 2)
        layout.addWidget(self.percent_label, 0, 3)
        layout.setColumnStretch(4, 1)

    def update_values(self, damage: int, percent: float, max_damage: int) -> None:
        self.bar.update_values(float(damage), float(max_damage))
        self.damage_label.setText(f"{damage:,}")
        self.percent_label.setText(f"{percent:.1f}%")


class _SlotDpsRow(QWidget):
    def __init__(self, slot: int) -> None:
        super().__init__()
        self.name_label = QLabel(f"{slot}")
        self.bar = _MetricBar()
        self.dps_label = QLabel("0.0")
        self.time_label = QLabel("0.0s")

        self.name_label.setObjectName("slotName")
        self.dps_label.setObjectName("metricValue")
        self.time_label.setObjectName("timeLabel")
        self.dps_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.addWidget(self.name_label, 0, 0)
        layout.addWidget(self.bar, 0, 1)
        layout.addWidget(self.dps_label, 0, 2)
        layout.addWidget(self.time_label, 0, 3)
        layout.setColumnStretch(4, 1)

    def update_values(self, dps: float, max_dps: float, active_seconds: float) -> None:
        self.bar.update_values(dps, max_dps)
        self.dps_label.setText(f"{dps:,.1f}")
        self.time_label.setText(f"{active_seconds:.1f}s")


class Overlay(QWidget):
    """Taskbar-visible floating window for live damage stats."""

    active_slot_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()

        self._locked = False
        self._drag_start: QPoint | None = None
        self.damage_rows = {slot: _SlotDamageRow(slot) for slot in (1, 2, 3)}
        self.dps_rows = {slot: _SlotDpsRow(slot) for slot in (1, 2, 3)}

        self.setWindowTitle("Damage Analyzer")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._apply_window_flags()
        self._build_ui()
        self._install_drag_filters()

        self.resize(500, 270)
        self.move(40, 40)

    def update_stats(self, stats: dict) -> None:
        total_damage = int(stats.get("total_damage", 0))
        slots = stats.get("slots", {})

        self.total_value_label.setText(f"{total_damage:,}")
        max_damage = max(
            [int(slot_data.get("damage", 0)) for slot_data in slots.values()] or [0]
        )
        max_dps = max(
            [float(slot_data.get("dps", 0.0)) for slot_data in slots.values()] or [0.0]
        )

        for slot, row in self.damage_rows.items():
            slot_data = slots.get(slot, {})
            damage = int(slot_data.get("damage", 0))
            percent = float(slot_data.get("percent", 0.0))
            row.update_values(damage, percent, max_damage)

        for slot, row in self.dps_rows.items():
            slot_data = slots.get(slot, {})
            row.update_values(
                float(slot_data.get("dps", 0.0)),
                max_dps,
                float(slot_data.get("active_seconds", 0.0)),
            )

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)

        if self._locked:
            painter.setBrush(QColor(24, 27, 32, 76))
            painter.setPen(QPen(QColor(255, 255, 255, 22), 1))
        else:
            painter.setBrush(QColor(24, 27, 32, 252))
            painter.setPen(QPen(QColor(95, 170, 255, 230), 2))

        painter.drawRoundedRect(rect, 8, 8)
        super().paintEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            not self._locked
            and event.button() == Qt.MouseButton.LeftButton
            and self._is_draggable_widget(self.childAt(event.position().toPoint()))
        ):
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start is not None and not self._locked:
            self.move(event.globalPosition().toPoint() - self._drag_start)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self._locked or not isinstance(event, QMouseEvent):
            return super().eventFilter(watched, event)

        if not self._is_draggable_widget(watched):
            return super().eventFilter(watched, event)

        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return True

        if event.type() == QEvent.Type.MouseMove and self._drag_start is not None:
            self.move(event.globalPosition().toPoint() - self._drag_start)
            event.accept()
            return True

        if event.type() == QEvent.Type.MouseButtonRelease:
            self._drag_start = None

        return super().eventFilter(watched, event)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Damage Analyzer")
        title.setObjectName("title")
        self.lock_button = QPushButton("锁定")
        self.close_button = QPushButton("关闭")
        self.lock_button.clicked.connect(self._toggle_lock)
        self.close_button.clicked.connect(self.close)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.lock_button)
        header.addWidget(self.close_button)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_damage_tab(), "输出")
        self.tabs.addTab(self._build_dps_tab(), "秒伤")

        root.addLayout(header)
        root.addWidget(self.tabs)

        self.setStyleSheet(
            """
            QLabel {
                color: #f6f7fb;
                font-family: "Segoe UI";
                font-size: 12px;
            }
            QLabel#title {
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#muted,
            QLabel#timeLabel,
            QLabel#percentLabel,
            QLabel#metricValue {
                color: #bbc3cf;
            }
            QLabel#slotName {
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
                min-width: 22px;
            }
            QLabel#totalValue {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#metricValue {
                min-width: 76px;
            }
            QLabel#percentLabel,
            QLabel#timeLabel {
                min-width: 54px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 30);
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 6px;
                color: #f6f7fb;
                min-height: 26px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 46);
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 38);
                border-radius: 7px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: rgba(255, 255, 255, 22);
                color: #cbd3df;
                border: 1px solid rgba(255, 255, 255, 30);
                border-bottom: none;
                min-width: 88px;
                padding: 7px 12px;
            }
            QTabBar::tab:selected {
                background-color: rgba(255, 255, 255, 52);
                color: #ffffff;
            }
            QWidget#metricBarTrack {
                background-color: rgba(255, 255, 255, 28);
                border: 1px solid rgba(255, 255, 255, 34);
                border-radius: 5px;
            }
            QLabel#metricBarFill {
                background-color: #23a6d5;
                border-radius: 5px;
            }
            """
        )

    def _build_damage_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("总输出")
        title.setObjectName("muted")
        self.total_value_label = QLabel("0")
        self.total_value_label.setObjectName("totalValue")
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.total_value_label)

        layout.addLayout(top)
        for row in self.damage_rows.values():
            layout.addWidget(row)
        layout.addStretch(1)
        return tab

    def _build_dps_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        heading = QGridLayout()
        heading.setHorizontalSpacing(10)
        heading.addWidget(QLabel("角色"), 0, 0)
        heading.addWidget(QLabel("占比"), 0, 1)
        heading.addWidget(QLabel("秒伤"), 0, 2)
        heading.addWidget(QLabel("时间"), 0, 3)
        heading.setColumnMinimumWidth(1, BAR_WIDTH)
        heading.setColumnStretch(4, 1)
        layout.addLayout(heading)

        for row in self.dps_rows.values():
            layout.addWidget(row)
        layout.addStretch(1)
        return tab

    def _toggle_lock(self) -> None:
        self._locked = not self._locked
        self.lock_button.setText("解锁" if self._locked else "锁定")
        self._apply_window_flags()
        self.update()
        self.show()

    def _apply_window_flags(self) -> None:
        flags = (
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowFlags(flags)

    def _install_drag_filters(self) -> None:
        self.installEventFilter(self)
        for widget in self.findChildren(QWidget):
            widget.installEventFilter(self)

    def _is_draggable_widget(self, widget: QObject | None) -> bool:
        while widget is not None:
            if isinstance(widget, (QPushButton, QTabBar)):
                return False
            widget = widget.parent()
            if widget is self:
                break
        return True
