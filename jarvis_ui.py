import os
import math
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QAction, QPainter, QColor
from config import BASE_PATH


class JarvisUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S - Just A Rather Very Intelligent System")
        self.setFixedSize(900, 620)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #020712;
                color: #00d4ff;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            """
        )

        self.tray_icon = None
        self.setup_tray_icon()

        self.logs = []
        self.is_speaking = False
        self._pulse_phase = 0.0
        self._face_scale = 1.0
        self.face_base_size = 260

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addStretch()

        self.orb_label = QLabel()
        self.orb_label.setFixedSize(340, 340)
        self.orb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.orb_label, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        self.status_label = QLabel("Status: Inicializando…")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #67e8f9; font-size: 18px;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        self.gesture_label = QLabel(self)
        self.gesture_label.setFixedSize(260, 180)
        self.gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gesture_label.setStyleSheet(
            """
            QLabel {
                border: 1px solid #00d4ff;
                border-radius: 8px;
                background-color: #000814;
            }
            """
        )
        self.gesture_label.hide()

        orb_path = os.path.join(BASE_PATH, "assets", "pngegg.png")
        self.orb_pixmap_original = QPixmap(orb_path)
        self._update_face_pixmap(self.face_base_size)

        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._animate_face)
        self.pulse_timer.start(30)

    def _update_face_pixmap(self, size):
        if self.orb_pixmap_original.isNull():
            fallback = QPixmap(size, size)
            fallback.fill(Qt.GlobalColor.transparent)
            painter = QPainter(fallback)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#00d4ff"))
            painter.drawEllipse(0, 0, size, size)
            painter.end()
            self.orb_label.setPixmap(fallback)
            return

        pixmap = self.orb_pixmap_original.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.orb_label.setPixmap(pixmap)

    def _animate_face(self):
        self._pulse_phase += 0.24 if self.is_speaking else 0.09

        if self.is_speaking:
            target = 1.06 + 0.14 * (0.5 + 0.5 * math.sin(self._pulse_phase))
        else:
            target = 1.0 + 0.02 * math.sin(self._pulse_phase)

        self._face_scale += (target - self._face_scale) * 0.28
        current_size = max(150, int(self.face_base_size * self._face_scale))
        self._update_face_pixmap(current_size)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        margin = 16
        x = self.width() - self.gesture_label.width() - margin
        y = margin
        self.gesture_label.move(x, y)

    def show_gesture_frame(self, pixmap):
        if self.gesture_label.isVisible():
            scaled = pixmap.scaled(
                self.gesture_label.width(),
                self.gesture_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.gesture_label.setPixmap(scaled)

    def show_status(self, text):
        self.status_label.setText(f"Status: {text}")

    def add_log(self, text):
        self.logs.append(text)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]

    def start_speaking(self):
        self.is_speaking = True

    def stop_speaking(self):
        self.is_speaking = False

    def show(self):
        super().show()

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)

        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor("#00ffff"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(8, 8, 48, 48)
        painter.end()

        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("JARVIS - Assistente Virtual")

        tray_menu = QMenu()

        restore_action = QAction("Restaurar", self)
        restore_action.triggered.connect(self.show_window)
        tray_menu.addAction(restore_action)

        hide_action = QAction("Minimizar para bandeja", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        self.show()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "JARVIS",
            "Minimizado para bandeja. Clique duplo no ícone para restaurar.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def quit_application(self):
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

