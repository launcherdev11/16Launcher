import datetime

from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ConsoleWidget(QWidget):
    # виджет консоли для отображения логов запуска игры

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Настройка интерфейса консоли"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(5)

        header_layout = QHBoxLayout()

        self.title_label = QLabel("Консоль запуска")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                padding: 2px 5px;
            }
        """)

        # Кнопка очистки консоли
        self.clear_button = QPushButton("Очистить")
        self.clear_button.setFixedSize(60, 25)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 3px;
                color: white;
                font-size: 11px;
                padding: 2px 4px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        self.clear_button.clicked.connect(self.clear_console)

        # Кнопка закрытия консоли
        self.close_button = QPushButton("Закрыть")
        self.close_button.setFixedSize(60, 25)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 3px;
                color: white;
                font-size: 11px;
                padding: 2px 4px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        self.close_button.clicked.connect(self.hide_console)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.clear_button)
        header_layout.addWidget(self.close_button)

        layout.addLayout(header_layout)

        # Текстовая область для логов
        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.console_text.setFixedHeight(200)

        # Настройка стилей консоли
        self.console_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #555555;
                border-radius: 5px;
                color: #ffffff;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 11px;
                padding: 5px;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
        """)

        # Установка моноширинного шрифта
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Monaco", 10)
            if not font.exactMatch():
                font = QFont("Courier New", 10)
        self.console_text.setFont(font)

        layout.addWidget(self.console_text)

        # Автопрокрутка
        self.auto_scroll = True

    def add_log(self, message: str):
        """Добавить сообщение в консоль"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        # Добавляем сообщение
        self.console_text.append(formatted_message)

        # Автопрокрутка к концу
        if self.auto_scroll:
            cursor = self.console_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.console_text.setTextCursor(cursor)

        # Ограничиваем количество строк (оставляем последние 1000 строк)
        self.limit_lines()

    def add_log_with_color(self, message: str, color: str = "#ffffff"):
        """Добавить сообщение с определенным цветом"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # Определяем цвет на основе типа сообщения
        if "[ERROR]" in message or "ERROR" in message or "Failed" in message:
            color = "#ff6b6b"  # Красный для ошибок
        elif "[WARN]" in message or "WARNING" in message:
            color = "#ffa500"  # Оранжевый для предупреждений
        elif (
            "[SUCCESS]" in message
            or "successfully" in message.lower()
            or "completed" in message.lower()
        ):
            color = "#4ecdc4"  # Зеленый для успеха
        elif "[INSTALL]" in message or "[BUILD]" in message:
            color = "#74c0fc"  # Голубой для процессов
        elif "[LAUNCH]" in message:
            color = "#8ce99a"  # Светло-зеленый для запуска
        else:
            color = "#ffffff"  # Белый по умолчанию

        formatted_message = (
            f'<span style="color: {color};">[{timestamp}] {message}</span>'
        )
        self.console_text.append(formatted_message)

        # Автопрокрутка к концу
        if self.auto_scroll:
            cursor = self.console_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.console_text.setTextCursor(cursor)

        self.limit_lines()

    def clear_console(self):
        """Очистить консоль"""
        self.console_text.clear()
        self.add_log_with_color("Консоль очищена", "#74c0fc")

    def limit_lines(self):
        """Ограничить количество строк в консоли"""
        document = self.console_text.document()
        if document.blockCount() > 1000:
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.Start)
            for _ in range(100):  # Удаляем первые 100 строк
                cursor.select(QTextCursor.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()  # Удаляем символ новой строки

    def set_visible(self, visible: bool):
        """Показать/скрыть консоль"""
        super().setVisible(visible)

    def show_console(self):
        """Показать консоль"""
        self.setVisible(True)
        self.add_log_with_color("Консоль запуска активирована", "#74c0fc")

    def hide_console(self):
        """Скрыть консоль"""
        self.setVisible(False)
