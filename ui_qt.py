import json
import sys
from pathlib import Path

import pyautogui
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSlider,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from monitor_logic import FastBarMonitor


SETTINGS_FILENAME = "auto_flask_settings.json"


class LogBridge(QObject):
    message = Signal(str)


class Section(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("section")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 14, 16, 16)
        self.layout.setSpacing(12)

        label = QLabel(title)
        label.setObjectName("sectionTitle")
        self.layout.addWidget(label)


class AutoFlaskWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("POE Auto Flask")
        self.resize(860, 640)
        self.setMinimumSize(760, 560)

        self.log_bridge = LogBridge()
        self.log_bridge.message.connect(self.write_log)
        self.monitor = FastBarMonitor(self.log_bridge.message.emit)
        self.settings_path = self.get_settings_path()
        self.coord_session = None

        self.load_settings()
        self.build_ui()
        self.apply_styles()
        self.refresh_controls()

        self.stop_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.stop_shortcut.activated.connect(self.stop_aura_bot)
        self.write_log("Ready.")

    def get_settings_path(self):
        app_path = Path(sys.executable if getattr(sys, "frozen", False) else __file__)
        return app_path.resolve().parent / SETTINGS_FILENAME

    def load_settings(self):
        if not self.settings_path.exists():
            return

        try:
            settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            self.log_bridge.message.emit(f"Could not load saved settings: {error}")
            return

        self.monitor.hp_coords = self.clean_coords(settings.get("hp_coords"))
        self.monitor.mana_coords = self.clean_coords(settings.get("mana_coords"))
        self.monitor.aura_color = self.clean_color(settings.get("aura_color"))
        self.monitor.hp_threshold = float(settings.get("hp_threshold", self.monitor.hp_threshold))
        self.monitor.mana_threshold = float(settings.get("mana_threshold", self.monitor.mana_threshold))
        self.monitor.hp_key = str(settings.get("hp_key", self.monitor.hp_key))
        self.monitor.mana_key = str(settings.get("mana_key", self.monitor.mana_key))
        self.monitor.poll_interval = float(settings.get("poll_interval", self.monitor.poll_interval))
        self.monitor.debug_logging = bool(settings.get("debug_logging", self.monitor.debug_logging))

    def clean_coords(self, coords):
        if not isinstance(coords, list) or len(coords) != 4:
            return None
        try:
            return tuple(int(value) for value in coords)
        except (TypeError, ValueError):
            return None

    def clean_color(self, color):
        if not isinstance(color, list) or len(color) != 3:
            return None
        try:
            return tuple(max(0, min(255, int(value))) for value in color)
        except (TypeError, ValueError):
            return None

    def save_settings(self):
        settings = {
            "hp_coords": list(self.monitor.hp_coords) if self.monitor.hp_coords else None,
            "mana_coords": list(self.monitor.mana_coords) if self.monitor.mana_coords else None,
            "aura_color": list(self.monitor.aura_color) if self.monitor.aura_color else None,
            "hp_threshold": self.monitor.hp_threshold,
            "mana_threshold": self.monitor.mana_threshold,
            "hp_key": self.monitor.hp_key,
            "mana_key": self.monitor.mana_key,
            "poll_interval": self.monitor.poll_interval,
            "debug_logging": self.monitor.debug_logging,
        }

        try:
            self.settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        except OSError as error:
            self.write_log(f"Could not save settings: {error}")

    def build_ui(self):
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 18, 16, 18)
        sidebar_layout.setSpacing(14)

        title = QLabel("POE Auto Flask")
        title.setObjectName("appTitle")
        sidebar_layout.addWidget(title)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        for label in ("Flask", "Aura Bot"):
            self.nav.addItem(QListWidgetItem(label))
        self.nav.currentRowChanged.connect(self.change_page)
        sidebar_layout.addWidget(self.nav)
        sidebar_layout.addStretch()

        self.status_label = QLabel("Idle")
        self.status_label.setObjectName("status")
        sidebar_layout.addWidget(self.status_label)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_flask_page())
        self.stack.addWidget(self.build_aura_page())

        root_layout.addWidget(sidebar, 0)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.nav.setCurrentRow(0)

    def build_flask_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        header = QLabel("Flask")
        header.setObjectName("pageTitle")
        layout.addWidget(header)

        self.hp_threshold_slider, self.hp_key_input, self.hp_value_label = self.add_bar_section(
            layout,
            "HP",
            self.monitor.hp_threshold,
            self.monitor.hp_key,
            self.set_hp_bar,
            self.update_hp_threshold,
            self.update_hp_key,
        )
        self.mana_threshold_slider, self.mana_key_input, self.mana_value_label = self.add_bar_section(
            layout,
            "Mana",
            self.monitor.mana_threshold,
            self.monitor.mana_key,
            self.set_mana_bar,
            self.update_mana_threshold,
            self.update_mana_key,
        )

        performance = Section("Performance")
        perf_grid = QGridLayout()
        perf_grid.setHorizontalSpacing(12)
        perf_grid.setVerticalSpacing(10)
        performance.layout.addLayout(perf_grid)

        perf_grid.addWidget(QLabel("Poll interval"), 0, 0)
        self.poll_slider = QSlider(Qt.Horizontal)
        self.poll_slider.setRange(80, 400)
        self.poll_slider.setValue(int(self.monitor.poll_interval * 1000))
        self.poll_slider.sliderReleased.connect(self.update_poll_interval)
        perf_grid.addWidget(self.poll_slider, 0, 1)
        self.poll_value_label = QLabel(f"{self.poll_slider.value()} ms")
        self.poll_value_label.setObjectName("muted")
        perf_grid.addWidget(self.poll_value_label, 0, 2)

        self.debug_checkbox = QCheckBox("Verbose debug log")
        self.debug_checkbox.setChecked(self.monitor.debug_logging)
        self.debug_checkbox.toggled.connect(self.update_debug_logging)
        perf_grid.addWidget(self.debug_checkbox, 1, 0, 1, 3)
        layout.addWidget(performance)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("log")
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text, 1)

        controls = QHBoxLayout()
        self.flask_button = QPushButton("Start Monitoring")
        self.flask_button.setObjectName("primary")
        self.flask_button.clicked.connect(self.toggle_monitoring)
        controls.addWidget(self.flask_button, 1)

        reset = QPushButton("Reset Bars")
        reset.clicked.connect(self.reset_bar_settings)
        controls.addWidget(reset)
        layout.addLayout(controls)

        return page

    def add_bar_section(self, parent_layout, title, threshold, key, set_bar, update_threshold, update_key):
        section = Section(f"{title} Settings")
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        section.layout.addLayout(grid)

        grid.addWidget(QLabel("Threshold"), 0, 0)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(threshold))
        slider.sliderReleased.connect(update_threshold)
        grid.addWidget(slider, 0, 1)
        value_label = QLabel(f"{int(threshold)}%")
        value_label.setObjectName("muted")
        grid.addWidget(value_label, 0, 2)

        grid.addWidget(QLabel("Flask key"), 1, 0)
        key_input = QLineEdit(key)
        key_input.setMaximumWidth(80)
        key_input.editingFinished.connect(update_key)
        grid.addWidget(key_input, 1, 1)

        button = QPushButton(f"Set {title} Bar")
        button.clicked.connect(set_bar)
        grid.addWidget(button, 1, 2)

        parent_layout.addWidget(section)
        return slider, key_input, value_label

    def build_aura_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        header = QLabel("Aura Bot")
        header.setObjectName("pageTitle")
        layout.addWidget(header)

        settings = Section("Aura Pathing")
        row = QHBoxLayout()
        self.aura_color_chip = QLabel()
        self.aura_color_chip.setObjectName("colorChip")
        row.addWidget(self.aura_color_chip)

        set_color = QPushButton("Set Aura Color")
        set_color.clicked.connect(self.set_aura_bar)
        row.addWidget(set_color)

        reset = QPushButton("Reset Aura Color")
        reset.clicked.connect(self.reset_aura_bar)
        row.addWidget(reset)
        row.addStretch()
        settings.layout.addLayout(row)
        layout.addWidget(settings)

        self.aura_log_text = QTextEdit()
        self.aura_log_text.setObjectName("log")
        self.aura_log_text.setReadOnly(True)
        layout.addWidget(self.aura_log_text, 1)

        controls = QHBoxLayout()
        self.aura_button = QPushButton("Start Aura Bot")
        self.aura_button.setObjectName("primary")
        self.aura_button.clicked.connect(self.toggle_aura_bot)
        controls.addWidget(self.aura_button, 1)
        layout.addLayout(controls)

        return page

    def apply_styles(self):
        self.setStyleSheet(
            """
            QWidget {
                background: #101820;
                color: #dce6ee;
                font-family: Segoe UI;
                font-size: 10pt;
            }
            #sidebar {
                background: #0b1117;
                border-right: 1px solid #243442;
                min-width: 190px;
                max-width: 190px;
            }
            #appTitle {
                color: #f6f8fb;
                font-size: 18pt;
                font-weight: 700;
            }
            #pageTitle {
                color: #f6f8fb;
                font-size: 20pt;
                font-weight: 700;
            }
            #section {
                background: #18242e;
                border: 1px solid #2e3c48;
                border-radius: 8px;
            }
            #sectionTitle {
                color: #f6f8fb;
                font-size: 11pt;
                font-weight: 700;
            }
            #muted {
                color: #94a3af;
            }
            #status {
                color: #8fbf7f;
                font-weight: 700;
            }
            #nav {
                background: transparent;
                border: 0;
                outline: 0;
            }
            #nav::item {
                padding: 10px 12px;
                border-radius: 6px;
            }
            #nav::item:selected {
                background: #2d6cdf;
                color: white;
            }
            QPushButton {
                background: #233241;
                border: 1px solid #344656;
                border-radius: 6px;
                color: #f6f8fb;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background: #2d4254;
            }
            QPushButton#primary {
                background: #2d6cdf;
                border-color: #3b7ff0;
            }
            QPushButton#danger {
                background: #8f3f4a;
                border-color: #a64a56;
            }
            QLineEdit, QTextEdit {
                background: #0b1117;
                border: 1px solid #243442;
                border-radius: 6px;
                color: #dce6ee;
                selection-background-color: #2d6cdf;
            }
            QLineEdit {
                padding: 7px 9px;
            }
            QTextEdit#log {
                font-family: Consolas;
                font-size: 9pt;
                padding: 8px;
            }
            QSlider::groove:horizontal {
                background: #0b1117;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #dce6ee;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QCheckBox {
                spacing: 8px;
            }
            #colorChip {
                border: 1px solid #344656;
                border-radius: 6px;
                min-width: 120px;
                max-width: 120px;
                min-height: 34px;
            }
            """
        )

    def change_page(self, index):
        self.stack.setCurrentIndex(index)

    def keyPressEvent(self, event):
        if self.coord_session and event.key() in (Qt.Key_F2, Qt.Key_F3):
            if event.key() == Qt.Key_F2:
                self.capture_start_point()
            else:
                self.capture_end_point()
            event.accept()
            return
        super().keyPressEvent(event)

    def start_coord_capture(self, bar_type):
        if self.coord_session:
            self.finish_coord_capture(cancel=True)

        self.coord_session = {"bar_type": bar_type, "coords": []}
        self.status_label.setText(f"{bar_type}: press F2 then F3")
        self.write_log(f"Capture {bar_type} with F2 and F3.")

    def capture_start_point(self):
        if not self.coord_session:
            return
        x, y = pyautogui.position()
        self.coord_session["coords"].append((x, y))
        self.write_log(f"{self.coord_session['bar_type']} start: {x}, {y}")

    def capture_end_point(self):
        if not self.coord_session:
            return
        x, y = pyautogui.position()
        self.coord_session["coords"].append((x, y))
        self.write_log(f"{self.coord_session['bar_type']} end: {x}, {y}")
        if len(self.coord_session["coords"]) >= 2:
            self.finish_coord_capture()

    def finish_coord_capture(self, cancel=False):
        session = self.coord_session
        self.coord_session = None
        if cancel or not session:
            self.status_label.setText("Idle")
            return

        coords = session["coords"]
        if len(coords) < 2:
            self.status_label.setText("Idle")
            return

        bar_type = session["bar_type"]
        bar_coords = (coords[0][0], coords[0][1], coords[1][0], coords[1][1])
        if bar_type == "HP":
            self.monitor.hp_coords = bar_coords
            self.write_log("HP bar coordinates saved.")
        elif bar_type == "Mana":
            self.monitor.mana_coords = bar_coords
            self.write_log("Mana bar coordinates saved.")
        else:
            aura_color = self.monitor.sample_exact_color(bar_coords)
            if not aura_color:
                self.write_log("Could not sample Aura color.")
                self.status_label.setText("Idle")
                return
            self.monitor.aura_color = aura_color
            self.write_log(f"Aura exact color saved: RGB {aura_color}.")

        self.save_settings()
        self.status_label.setText("Idle")
        self.refresh_controls()

    def set_hp_bar(self):
        self.start_coord_capture("HP")

    def set_mana_bar(self):
        self.start_coord_capture("Mana")

    def set_aura_bar(self):
        self.start_coord_capture("Aura")

    def update_hp_threshold(self):
        self.monitor.hp_threshold = self.hp_threshold_slider.value()
        self.hp_value_label.setText(f"{self.monitor.hp_threshold:.0f}%")
        self.save_settings()
        self.write_log(f"HP threshold updated to {self.monitor.hp_threshold:.0f}%.")

    def update_mana_threshold(self):
        self.monitor.mana_threshold = self.mana_threshold_slider.value()
        self.mana_value_label.setText(f"{self.monitor.mana_threshold:.0f}%")
        self.save_settings()
        self.write_log(f"Mana threshold updated to {self.monitor.mana_threshold:.0f}%.")

    def update_hp_key(self):
        self.monitor.hp_key = self.hp_key_input.text().strip() or self.monitor.hp_key
        self.hp_key_input.setText(self.monitor.hp_key)
        self.save_settings()
        self.write_log(f"HP flask key updated to '{self.monitor.hp_key}'.")

    def update_mana_key(self):
        self.monitor.mana_key = self.mana_key_input.text().strip() or self.monitor.mana_key
        self.mana_key_input.setText(self.monitor.mana_key)
        self.save_settings()
        self.write_log(f"Mana flask key updated to '{self.monitor.mana_key}'.")

    def update_poll_interval(self):
        interval_ms = self.poll_slider.value()
        self.monitor.poll_interval = interval_ms / 1000
        self.poll_value_label.setText(f"{interval_ms} ms")
        self.save_settings()
        self.write_log(f"Poll interval updated to {interval_ms} ms.")

    def update_debug_logging(self, checked):
        self.monitor.debug_logging = checked
        self.save_settings()
        self.write_log(f"Verbose debug log {'enabled' if checked else 'disabled'}.")

    def toggle_monitoring(self):
        self.monitor.toggle_monitoring()
        self.refresh_controls()

    def toggle_aura_bot(self):
        self.monitor.toggle_aura_bot()
        self.refresh_controls()

    def stop_aura_bot(self):
        self.monitor.stop_aura_bot()
        self.refresh_controls()

    def reset_bar_settings(self):
        self.monitor.hp_coords = None
        self.monitor.mana_coords = None
        self.monitor.hp_buffer.clear()
        self.monitor.mana_buffer.clear()
        self.monitor.previous_hp_percentage = 100
        self.monitor.previous_mana_percentage = 100
        self.save_settings()
        self.write_log("Saved bar coordinates reset.")
        self.refresh_controls()

    def reset_aura_bar(self):
        self.monitor.stop_aura_bot()
        self.monitor.aura_color = None
        self.save_settings()
        self.write_log("Saved Aura color reset.")
        self.refresh_controls()

    def refresh_controls(self):
        flask_running = self.monitor.monitoring
        aura_running = self.monitor.aura_monitoring

        self.flask_button.setText("Pause Monitoring" if flask_running else "Start Monitoring")
        self.flask_button.setObjectName("danger" if flask_running else "primary")
        self.flask_button.style().unpolish(self.flask_button)
        self.flask_button.style().polish(self.flask_button)

        self.aura_button.setText("Stop Aura Bot" if aura_running else "Start Aura Bot")
        self.aura_button.setObjectName("danger" if aura_running else "primary")
        self.aura_button.style().unpolish(self.aura_button)
        self.aura_button.style().polish(self.aura_button)

        if aura_running:
            self.status_label.setText("Aura Bot")
        elif flask_running:
            self.status_label.setText("Monitoring")
        elif self.coord_session:
            self.status_label.setText(f"{self.coord_session['bar_type']}: press F2 then F3")
        else:
            self.status_label.setText("Idle")

        if self.monitor.aura_color:
            r, g, b = self.monitor.aura_color
            color = QColor(r, g, b)
            text_color = "#101820" if color.lightness() > 150 else "#f6f8fb"
            self.aura_color_chip.setText(f"RGB {r}, {g}, {b}")
            self.aura_color_chip.setStyleSheet(
                f"background: rgb({r}, {g}, {b}); color: {text_color};"
                "border: 1px solid #344656; border-radius: 6px; padding: 8px;"
            )
        else:
            self.aura_color_chip.setText("No color")
            self.aura_color_chip.setStyleSheet(
                "background: #0b1117; color: #94a3af;"
                "border: 1px solid #344656; border-radius: 6px; padding: 8px;"
            )

    def write_log(self, message):
        line = message.rstrip()
        if not line:
            return
        if hasattr(self, "log_text"):
            self.log_text.append(line)
        if hasattr(self, "aura_log_text"):
            self.aura_log_text.append(line)

    def closeEvent(self, event):
        if self.monitor.monitoring:
            self.monitor.toggle_monitoring()
        self.monitor.stop_aura_bot()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = AutoFlaskWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
