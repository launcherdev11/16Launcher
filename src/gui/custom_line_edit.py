from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget, QSizePolicy, QToolButton

from util import resource_path


class CustomLineEdit(QLineEdit):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._btn = None
    
    def set_button(self, button):
        # Прикрепляем внешнюю кнопку внутрь поля справа
        self._btn = button
        if self._btn:
            try:
                self._btn.setParent(self)
                self._btn.raise_()
            except Exception:
                pass
            self._update_text_margins()
            self._reposition_button()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_button()

    def _update_text_margins(self) -> None:
        if self._btn:
            self.setTextMargins(8, 0, self._btn.width() + 10, 0)

    def _reposition_button(self) -> None:
        if not self._btn:
            return
        right_padding = 8
        x = self.rect().right() - right_padding - self._btn.width()
        y = (self.rect().height() - self._btn.height()) // 2
        self._btn.move(x, y)


class SearchLineEdit(QLineEdit):
    
    searchClicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._btn = QToolButton(self)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setIcon(QIcon(resource_path('assets/search.png')))
        self._btn.setToolTip('Поиск')
        self._btn.setStyleSheet('QToolButton { border: none; background: transparent; padding: 0px; }')
        self._btn.setFixedSize(20, 20)
        self._btn.clicked.connect(self.searchClicked.emit)

        self.setClearButtonEnabled(True)
        self._update_text_margins()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        right_padding = 8
        x = self.rect().right() - right_padding - self._btn.width()
        y = (self.rect().height() - self._btn.height()) // 2
        self._btn.move(x, y)
    
    def _update_text_margins(self) -> None:
        self.setTextMargins(8, 0, self._btn.width() + 10, 0)