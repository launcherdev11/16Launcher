import logging
import os
import subprocess

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from config import MINECRAFT_DIR, MODS_DIR
from util import load_settings, resource_path, save_settings
from util import load_settings, resource_path, save_settings


class SettingsTab(QWidget):
    def __init__(self, translator, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()

    def setup_ui(self):
        app = QApplication.instance()
        app.setStyleSheet("""
            QLabel {
                font-size: 15px;
                color: #ffffff;
            }
            QPushButton {
                font-size: 15px;
            }
            QLineEdit {
                font-size: 15px;
            }
            QComboBox {
                font-size: 15px;
            }
            QCheckBox {
                font-size: 15px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Создаем скролл-область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
        """)

        # Контейнер для всех настроек
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(10)

        # Стили для карточек
        card_style = """
            QWidget {
                background-color: #232323;
                border-radius: 7px;
                padding: 8px 10px 8px 10px;
            }
        """
        header_style = 'font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 2px;'

        # Внешний вид
        appearance_card = QWidget()
        appearance_card.setStyleSheet(card_style)
        appearance_layout = QVBoxLayout(appearance_card)
        appearance_layout.setSpacing(7)

        appearance_header = QLabel('Внешний вид')
        appearance_header.setStyleSheet(header_style)
        appearance_layout.addWidget(appearance_header)

        # Язык
        language_layout = QHBoxLayout()
        language_label = QLabel('Язык:')
        language_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.language_combo = QComboBox()
        self.language_combo.addItem('Русский', 'ru')
        self.language_combo.addItem('English', 'en')
        self.language_combo.setStyleSheet("""
            QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 2px 5px;
                color: white;
                min-width: 90px;
                font-size: 15px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        appearance_layout.addLayout(language_layout)

        #консоль

        # Тема
        self.theme_button = QPushButton()
        self.theme_button.setFixedHeight(32)
        self.update_theme_button_icon()
        self.theme_button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px;
                text-align: left;
                color: white;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        self.theme_button.clicked.connect(self.toggle_theme)
        appearance_layout.addWidget(self.theme_button)

        settings_layout.addWidget(appearance_card)

        # Игровые настройки
        game_card = QWidget()
        game_card.setStyleSheet(card_style)
        game_layout = QVBoxLayout(game_card)
        game_layout.setSpacing(15)

        game_header = QLabel('Игровые настройки')
        game_header.setStyleSheet(header_style)
        game_layout.addWidget(game_header)

        # Память
        memory_layout = QVBoxLayout()
        memory_label = QLabel('Оперативная память (ГБ)')
        memory_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.memory_slider = QSlider(Qt.Orientation.Horizontal)
        self.memory_slider.setRange(1, 32)
        self.memory_slider.setValue(4)
        self.memory_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 8px;
                background: #3d3d3d;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #bbbbbb;
                border: 1px solid #777777;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #d0d0d0;
            }
        """)
        self.memory_value_label = QLabel('4 ГБ')
        self.memory_value_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.memory_slider.valueChanged.connect(self.update_memory_label)
        # Сохраняем значение памяти при отпускании ползунка и при изменении (на случай управления с клавиатуры)
        self.memory_slider.sliderReleased.connect(self.save_memory_setting)
        self.memory_slider.valueChanged.connect(self.save_memory_setting)
        memory_layout.addWidget(memory_label)
        memory_layout.addWidget(self.memory_slider)
        memory_layout.addWidget(self.memory_value_label)
        game_layout.addLayout(memory_layout)

        #консоль
        self.show_console_checkbox = QCheckBox('Консоль при запуске')
        self.show_console_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 6px;
                font-size: 15px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #555555;
                border-radius: 2px;
                background: #3d3d3d;
            }
            QCheckBox::indicator:checked {
                background: #0078d7;
                border: 1px solid #0078d7;
            }
        """)
        self.show_console_checkbox.setChecked(True)
        game_layout.addWidget(self.show_console_checkbox)

        self.hide_console_checkbox = QCheckBox('Скрывать консоль после запуска')
        self.hide_console_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 6px;
                font-size: 15px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #555555;
                border-radius: 2px;
                background: #3d3d3d;
            }
            QCheckBox::indicator:checked {
                background: #0078d7;
                border: 1px solid #0078d7;
            }
        """)
        self.hide_console_checkbox.setChecked(False) 
        game_layout.addWidget(self.hide_console_checkbox)

        self.show_console_checkbox.toggled.connect(self.hide_console_checkbox.setVisible)
        self.show_console_checkbox.toggled.connect(self.save_console_settings)
        self.hide_console_checkbox.toggled.connect(self.save_console_settings)
        self.hide_console_checkbox.setVisible(self.show_console_checkbox.isChecked())

        self.close_on_launch_checkbox = QCheckBox('Закрывать лаунчер при запуске игры')
        self.close_on_launch_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 6px;
                font-size: 15px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #555555;
                border-radius: 2px;
                background: #3d3d3d;
            }
            QCheckBox::indicator:checked {
                background: #0078d7;
                border: 1px solid #0078d7;
            }
        """)
        game_layout.addWidget(self.close_on_launch_checkbox)

        self.check_running_processes_checkbox = QCheckBox('Проверять запущенные процессы Minecraft')
        self.check_running_processes_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 6px;
                font-size: 15px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #555555;
                border-radius: 2px;
                background: #3d3d3d;
            }
            QCheckBox::indicator:checked {
                background: #0078d7;
                border: 1px solid #0078d7;
            }
        """)
        self.check_running_processes_checkbox.setChecked(True)  # По умолчанию включено
        game_layout.addWidget(self.check_running_processes_checkbox)

        # Автоустановка Java (чекбокс в игровых настройках) - скрыт
        self.auto_java_checkbox_game = QCheckBox('Автоматическая установка Java')
        self.auto_java_checkbox_game.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 6px;
                font-size: 15px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #555555;
                border-radius: 2px;
                background: #3d3d3d;
            }
            QCheckBox::indicator:checked {
                background: #0078d7;
                border: 1px solid #0078d7;
            }
        """)
        self.auto_java_checkbox_game.setVisible(False)
        game_layout.addWidget(self.auto_java_checkbox_game)

        settings_layout.addWidget(game_card)

        # Директории
        directories_card = QWidget()
        directories_card.setStyleSheet(card_style)
        directories_layout = QVBoxLayout(directories_card)
        directories_layout.setSpacing(7)

        directories_header = QLabel('Директории')
        directories_header.setStyleSheet(header_style)
        directories_layout.addWidget(directories_header)

        input_style = """
            QLineEdit {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 6px;
                color: white;
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
        """
        button_style = """
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 2px 10px;
                color: white;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """

        # Директория игры
        game_dir_layout = QHBoxLayout()
        game_dir_label = QLabel('Игра:')
        game_dir_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.directory_edit = QLineEdit()
        self.directory_edit.setText(MINECRAFT_DIR)
        self.directory_edit.setStyleSheet(input_style)
        self.choose_directory_button = QPushButton('...')
        self.choose_directory_button.setFixedWidth(32)
        self.choose_directory_button.setStyleSheet(button_style)
        self.choose_directory_button.clicked.connect(self.choose_directory)
        game_dir_layout.addWidget(game_dir_label)
        game_dir_layout.addWidget(self.directory_edit)
        game_dir_layout.addWidget(self.choose_directory_button)
        directories_layout.addLayout(game_dir_layout)

        # Директория модов
        mods_dir_layout = QHBoxLayout()
        mods_dir_label = QLabel('Моды:')
        mods_dir_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.mods_directory_edit = QLineEdit()
        self.mods_directory_edit.setText(MODS_DIR)
        self.mods_directory_edit.setStyleSheet(input_style)
        self.choose_mods_directory_button = QPushButton('...')
        self.choose_mods_directory_button.setFixedWidth(32)
        self.choose_mods_directory_button.setStyleSheet(button_style)
        self.choose_mods_directory_button.clicked.connect(self.choose_mods_directory)
        mods_dir_layout.addWidget(mods_dir_label)
        mods_dir_layout.addWidget(self.mods_directory_edit)
        mods_dir_layout.addWidget(self.choose_mods_directory_button)
        directories_layout.addLayout(mods_dir_layout)
        settings_layout.addWidget(directories_card)

        # Версии Minecraft
        versions_card = QWidget()
        versions_card.setStyleSheet(card_style)
        versions_layout = QVBoxLayout(versions_card)
        versions_layout.setSpacing(7)
        versions_header = QLabel('Версии Minecraft')
        versions_header.setStyleSheet(header_style)
        versions_layout.addWidget(versions_header)
        self.show_snapshots_checkbox = QCheckBox('Показывать Снапшоты')
        self.show_snapshots_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 6px;
                font-size: 15px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #555555;
                border-radius: 2px;
                background: #3d3d3d;
            }
            QCheckBox::indicator:checked {
                background: #0078d7;
                border: 1px solid #0078d7;
            }
        """)
        if 'show_snapshots' in self.parent_window.settings:
            self.show_snapshots_checkbox.setChecked(
                self.parent_window.settings['show_snapshots'],
            )
        self.show_snapshots_checkbox.stateChanged.connect(
            self.parent_window.update_version_list,
        )
        versions_layout.addWidget(self.show_snapshots_checkbox)

        # Автоустановка Java (дублирующий чекбокс в секции версий) - скрыт
        self.auto_java_checkbox_versions = QCheckBox('Автоматическая установка Java')
        self.auto_java_checkbox_versions.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 6px;
                font-size: 15px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #555555;
                border-radius: 2px;
                background: #3d3d3d;
            }
            QCheckBox::indicator:checked {
                background: #0078d7;
                border: 1px solid #0078d7;
            }
        """)
        self.auto_java_checkbox_versions.setVisible(False)
        versions_layout.addWidget(self.auto_java_checkbox_versions)
        settings_layout.addWidget(versions_card)

        # Аккаунт Ely.by
        if hasattr(self.parent_window, 'ely_session') and self.parent_window.ely_session:
            ely_card = QWidget()
            ely_card.setStyleSheet(card_style)
            ely_layout = QVBoxLayout(ely_card)
            ely_layout.setSpacing(7)
            ely_header = QLabel('Аккаунт Ely.by')
            ely_header.setStyleSheet(header_style)
            ely_layout.addWidget(ely_header)
            self.ely_logout_button = QPushButton('Выйти из Ely.by')
            self.ely_logout_button.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    padding: 4px;
                    border-radius: 4px;
                    border: none;
                    font-size: 15px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            self.ely_logout_button.clicked.connect(self.parent_window.ely_logout)
            ely_layout.addWidget(self.ely_logout_button)
            settings_layout.addWidget(ely_card)

        # Сборки
        builds_card = QWidget()
        builds_card.setStyleSheet(card_style)
        builds_layout = QVBoxLayout(builds_card)
        builds_layout.setSpacing(7)
        builds_header = QLabel('Сборки')
        builds_header.setStyleSheet(header_style)
        builds_layout.addWidget(builds_header)
        export_path_layout = QHBoxLayout()
        export_path_label = QLabel('Экспорт:')
        export_path_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.export_path_edit = QLineEdit()
        self.export_path_edit.setText(
            self.parent_window.settings.get('export_path', ''),
        )
        self.export_path_edit.setStyleSheet(input_style)
        self.export_path_btn = QPushButton('...')
        self.export_path_btn.setFixedWidth(32)
        self.export_path_btn.setStyleSheet(button_style)
        self.export_path_btn.clicked.connect(self.set_export_path)
        export_path_layout.addWidget(export_path_label)
        export_path_layout.addWidget(self.export_path_edit)
        export_path_layout.addWidget(self.export_path_btn)
        builds_layout.addLayout(export_path_layout)
        settings_layout.addWidget(builds_card)

        # Добавляем растягивающийся элемент в конец
        settings_layout.addStretch()

        # Устанавливаем контейнер в скролл
        scroll.setWidget(settings_container)
        main_layout.addWidget(scroll)

        # Загружаем настройки
        settings = self.parent_window.settings if self.parent_window else load_settings()
        if 'close_on_launch' in settings:
            self.close_on_launch_checkbox.setChecked(settings['close_on_launch'])
        if 'memory' in settings:
            try:
                value = int(settings['memory'])
            except Exception:
                value = 4
            value = max(self.memory_slider.minimum(), min(self.memory_slider.maximum(), value))
            self.memory_slider.setValue(value)
        if 'minecraft_directory' in settings:
            self.directory_edit.setText(settings['minecraft_directory'])
        if 'mods_directory' in settings:
            self.mods_directory_edit.setText(settings['mods_directory'])
        if 'show_console' in settings:
            self.show_console_checkbox.setChecked(settings['show_console'])
        if 'hide_console_after_launch' in settings:
            self.hide_console_checkbox.setChecked(settings['hide_console_after_launch'])
        if 'check_running_processes' in settings:
            self.check_running_processes_checkbox.setChecked(settings['check_running_processes'])
        if 'auto_install_java' in settings:
            checked = bool(settings['auto_install_java'])
            self.auto_java_checkbox_game.setChecked(checked)
            self.auto_java_checkbox_versions.setChecked(checked)
        else:
            # По умолчанию автоустановка Java отключена
            self.auto_java_checkbox_game.setChecked(False)
            self.auto_java_checkbox_versions.setChecked(False)

        # Синхронизация чекбоксов автоустановки Java
        self.auto_java_checkbox_game.toggled.connect(self._on_auto_java_toggled_from_game)
        self.auto_java_checkbox_versions.toggled.connect(self._on_auto_java_toggled_from_versions)

        # Обновляем подпись памяти под текущее значение
        self.update_memory_label()

        # Принудительно обновляем стили
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def update_memory_label(self):
        self.memory_value_label.setText(f'{self.memory_slider.value()} ГБ')

    def save_memory_setting(self):
        if self.parent_window and hasattr(self.parent_window, 'settings'):
            self.parent_window.settings['memory'] = self.memory_slider.value()
            save_settings(self.parent_window.settings)

    def choose_mods_directory(self):
        try:
            directory = QFileDialog.getExistingDirectory(
                self,
                'Выберите директорию для модов',
            )
            if directory:
                self.mods_directory_edit.setText(directory)
                # Сохраняем в настройках
                if self.parent_window:
                    self.parent_window.settings['mods_directory'] = directory
                    save_settings(self.parent_window.settings)
                    logging.info(f'Папка модов изменена на: {directory}')
        except Exception as e:
            logging.exception(f'Ошибка при выборе директории модов: {e}')
            self.show_error_message('Ошибка при выборе директории модов')

    def set_export_path(self):
        path = QFileDialog.getExistingDirectory(self, 'Выберите папку для экспорта')
        if path:
            self.export_path_edit.setText(path)
            self.parent_window.settings['export_path'] = path
            save_settings(self.parent_window.settings)

    def open_mods_directory(self):
        try:
            mods_dir = self.mods_directory_edit.text()
            if not os.path.exists(mods_dir):
                os.makedirs(mods_dir)
            if os.name == 'nt':
                subprocess.Popen(f'explorer "{mods_dir}"')
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', mods_dir])
        except Exception as e:
            logging.exception(f'Ошибка при открытии директории модов: {e}')
            self.show_error_message('Ошибка при открытии директории модов')

    def setup_language_selector(self):
        self.language_combo = QComboBox()
        self.language_combo.addItem('Русский', 'ru')
        self.language_combo.addItem('English', 'en')
        self.language_combo.currentIndexChanged.connect(self.change_language)

        language_layout = QHBoxLayout()
        language_label = QLabel('Язык:')
        language_label.setStyleSheet('color: #ffffff;')
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)

        appearance_layout = self.findChild(QVBoxLayout)
        if appearance_layout:
            appearance_layout.insertLayout(0, language_layout)

    def change_language(self):
        lang = self.language_combo.currentData()
        self.translator.set_language(lang)
        self.parent_window.retranslate_ui()

    def toggle_theme(self):
        """Переключает тему между светлой и темной"""
        current_theme = getattr(self.parent_window, 'current_theme', 'dark')
        new_theme = 'light' if current_theme == 'dark' else 'dark'

        self.parent_window.apply_dark_theme(
            new_theme == 'dark',
        )
        self.update_theme_button_icon()

        self.parent_window.settings['theme'] = new_theme
        save_settings(self.parent_window.settings)

    def update_theme_button_icon(self):
        current_theme = getattr(self.parent_window, 'current_theme', 'dark')
        if current_theme == 'dark':
            self.theme_button.setIcon(QIcon(resource_path('assets/sun.png')))
            self.theme_button.setText(' Светлая тема')
        else:
            self.theme_button.setIcon(QIcon(resource_path('assets/moon.png')))
            self.theme_button.setText(' Тёмная тема')
        self.theme_button.setIconSize(QSize(24, 24))

    def update_logout_button_visibility(self):
        """Обновляет видимость кнопки выхода из Ely.by"""
        # Проверяем, есть ли кнопка выхода
        if not hasattr(self, 'ely_logout_button'):
            logging.debug('ely_logout_button не найдена в SettingsTab')
            return
        
        # Проверяем наличие сессии
        has_session = hasattr(self.parent(), 'ely_session') and self.parent().ely_session
        self.ely_logout_button.setVisible(has_session)

    def choose_directory(self):
        try:
            directory = QFileDialog.getExistingDirectory(
                self,
                'Выберите директорию Minecraft',
            )
            if directory:
                self.directory_edit.setText(directory)
                # Сохраняем в настройках
                if self.parent_window:
                    self.parent_window.settings['minecraft_directory'] = directory
                    save_settings(self.parent_window.settings)
                    logging.info(f'Папка игры изменена на: {directory}')
        except Exception as e:
            logging.exception(f'Ошибка при выборе директории: {e}')
            self.show_error_message('Ошибка при выборе директории')

    def open_directory(self):
        try:
            if os.name == 'nt':
                subprocess.Popen(f'explorer "{MINECRAFT_DIR}"')
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', MINECRAFT_DIR])
        except Exception as e:
            logging.exception(f'Ошибка при открытии директории: {e}')
            self.show_error_message('Ошибка при открытии директории')

    def show_error_message(self, message):
        QMessageBox.critical(self, 'Ошибка', message)

    def save_console_settings(self):
        """Сохраняет настройки консоли"""
        if self.parent_window:
            self.parent_window.settings['show_console'] = self.show_console_checkbox.isChecked()
            self.parent_window.settings['hide_console_after_launch'] = self.hide_console_checkbox.isChecked()
            save_settings(self.parent_window.settings)

    def _on_auto_java_toggled_from_game(self, checked: bool):
        if self.parent_window:
            self.parent_window.settings['auto_install_java'] = bool(checked)
            save_settings(self.parent_window.settings)
        if self.auto_java_checkbox_versions.isChecked() != checked:
            self.auto_java_checkbox_versions.blockSignals(True)
            self.auto_java_checkbox_versions.setChecked(checked)
            self.auto_java_checkbox_versions.blockSignals(False)

    def _on_auto_java_toggled_from_versions(self, checked: bool):
        if self.parent_window:
            self.parent_window.settings['auto_install_java'] = bool(checked)
            save_settings(self.parent_window.settings)
        if self.auto_java_checkbox_game.isChecked() != checked:
            self.auto_java_checkbox_game.blockSignals(True)
            self.auto_java_checkbox_game.setChecked(checked)
            self.auto_java_checkbox_game.blockSignals(False)

    def closeEvent(self, event):
        if self.parent_window:
            self.parent_window.settings = {
                'close_on_launch': self.close_on_launch_checkbox.isChecked(),
                'memory': self.memory_slider.value(),
                'minecraft_directory': self.directory_edit.text(),
                'mods_directory': self.mods_directory_edit.text(),
                'show_console': self.show_console_checkbox.isChecked(),
                'hide_console_after_launch': self.hide_console_checkbox.isChecked(),
                'check_running_processes': self.check_running_processes_checkbox.isChecked()
            }
            save_settings(self.parent_window.settings)
