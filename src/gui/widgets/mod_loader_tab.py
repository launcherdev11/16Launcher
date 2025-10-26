import logging

from minecraft_launcher_lib.forge import find_forge_version
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import MINECRAFT_VERSIONS
from util import get_quilt_versions
from ..threads.mod_loader_installer import ModLoaderInstaller


class ModLoaderTab(QWidget):
    def __init__(self, loader_type, parent=None):
        super().__init__(parent)
        self.loader_type = loader_type
        self.setup_ui()
        # Загружаем версии только для доступных вкладок
        if self.loader_type not in ['optifine', 'quilt']:
            self.load_mc_versions()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Для optifine и quilt показываем сообщение о недоступности
        if self.loader_type == 'optifine':
            unavailable_label = QLabel('Вкладка OptiFine временно недоступна(')
            unavailable_label.setAlignment(Qt.AlignCenter)
            unavailable_label.setStyleSheet("""
                color: #f1f1f1;
                font-size: 18px;
                padding: 50px;
            """)
            layout.addWidget(unavailable_label)
            layout.addStretch()
            return
        
        if self.loader_type == 'quilt':
            unavailable_label = QLabel('Вкладка Quilt временно недоступна(')
            unavailable_label.setAlignment(Qt.AlignCenter)
            unavailable_label.setStyleSheet("""
                color: #f1f1f1;
                font-size: 18px;
                padding: 50px;
            """)
            layout.addWidget(unavailable_label)
            layout.addStretch()
            return

        # Выбор версии Minecraft
        self.mc_version_combo = QComboBox()
        layout.addWidget(QLabel('Версия Minecraft:'))
        layout.addWidget(self.mc_version_combo)

        # Для Forge - выбор версии Forge
        if self.loader_type == 'forge':
            self.forge_version_combo = QComboBox()
            layout.addWidget(QLabel('Версия Forge:'))
            layout.addWidget(self.forge_version_combo)
            self.mc_version_combo.currentTextChanged.connect(self.update_forge_versions)
            self.update_forge_versions()

        if self.loader_type == 'quilt':
            self.loader_version_combo = QComboBox()
            layout.addWidget(QLabel('Версия Quilt:'))
            layout.addWidget(self.loader_version_combo)
            self.mc_version_combo.currentTextChanged.connect(self.update_quilt_versions)
            self.update_quilt_versions()

        # Кнопка установки
        self.install_btn = QPushButton(f'Установить {self.loader_type}')
        self.install_btn.clicked.connect(self.install_loader)
        layout.addWidget(self.install_btn)

        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Статус
        self.status_label = QLabel()
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

    def load_mc_versions(self):
        """Загружает версии Minecraft"""
        self.mc_version_combo.clear()
        for version in MINECRAFT_VERSIONS:
            self.mc_version_combo.addItem(version)

    def update_forge_versions(self):
        """Обновляет список версий Forge при изменении версии MC"""
        if self.loader_type != 'forge':
            return

        mc_version = self.mc_version_combo.currentText()
        self.forge_version_combo.clear()

        try:
            forge_version = find_forge_version(mc_version)
            if forge_version:
                self.forge_version_combo.addItem(forge_version)
            else:
                self.forge_version_combo.addItem('Автоматический выбор')
        except Exception as e:
            logging.exception(f'Ошибка загрузки Forge: {e!s}')
            self.forge_version_combo.addItem('Ошибка загрузки')

    def update_quilt_versions(self):
        """Обновляет список версий Quilt"""
        if self.loader_type != 'quilt':
            return

        self.loader_version_combo.clear()
        try:
            versions = get_quilt_versions(self.mc_version_combo.currentText())
            for v in versions:
                self.loader_version_combo.addItem(v['version'])
            if versions:
                self.loader_version_combo.setCurrentIndex(0)
        except Exception as e:
            logging.exception(f'Ошибка загрузки Quilt: {e}')
            self.loader_version_combo.addItem('Ошибка загрузки')

    def install_loader(self):
        mc_version = self.mc_version_combo.currentText()

        if self.loader_type == 'forge':
            forge_version = self.forge_version_combo.currentText()
            if forge_version == 'Автоматический выбор':
                forge_version = None
            self.install_thread = ModLoaderInstaller('forge', forge_version, mc_version)
        elif self.loader_type == 'quilt':
            loader_version = self.loader_version_combo.currentText()
            self.install_thread = ModLoaderInstaller(
                'quilt',
                loader_version,  # Передаем версию лоадера
                mc_version,
            )
        else:
            self.install_thread = ModLoaderInstaller(self.loader_type, None, mc_version)

        self.install_thread.progress_signal.connect(self.update_progress)
        self.install_thread.finished_signal.connect(self.installation_finished)
        self.install_thread.start()

        self.install_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setVisible(True)

    def update_progress(self, current, total, text):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.status_label.setText(text)

    def installation_finished(self, success, message):
        self.install_btn.setEnabled(True)
        self.progress.setVisible(False)

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information if success else QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle('Результат установки')
        msg.exec_()