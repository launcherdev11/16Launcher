from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from util import resource_path


class SplashScreen(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("16Launcher")
        self.setFixedSize(600, 400)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Фоновый виджет
        self.background: QWidget = QWidget(self)
        self.background.setObjectName("splashBackground")
        self.background.setStyleSheet("""
            #splashBackground {
                background-color: #1A1A1A;
                border-radius: 20px;
                border: 2px solid #333333;
            }
        """)

        content_layout = QVBoxLayout(self.background)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(20)

        self.logo = QLabel()
        pixmap = QPixmap(resource_path("assets/icon.ico")).scaled(
            200,
            200,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.logo.setPixmap(pixmap)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.logo)

        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                height: 8px;
                background: #126915;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1b7f1e, stop:1 #08590b);
                border-radius: 4px;
            }
        """)
        content_layout.addWidget(self.progress)

        # Статус
        self.status_label = QLabel("Инициализация...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #AAAAAA; font-size: 14px;")
        content_layout.addWidget(self.status_label)

        # Версия
        version_label = QLabel("Версия 1.0.3")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #666666; font-size: 12px;")
        content_layout.addWidget(version_label)

        layout.addWidget(self.background)

    def update_progress(self, value: int, message: str) -> None:
        self.progress.setValue(value)
        self.status_label.setText(message)
        QApplication.processEvents()
