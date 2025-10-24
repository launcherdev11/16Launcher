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
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #666666;
                min-height: 16px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
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
                background: #0078d7;
                border: none;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1a88e0;
            }
        """)
        self.memory_value_label = QLabel('4 ГБ')
        self.memory_value_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.memory_slider.valueChanged.connect(self.update_memory_label)
        memory_layout.addWidget(memory_label)
        memory_layout.addWidget(self.memory_slider)
        memory_layout.addWidget(self.memory_value_label)
        game_layout.addLayout(memory_layout)

        # Чекбокс закрытия
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

        settings_layout.addWidget(game_card)

        # Директории
        directories_card = QWidget()
        directories_card.setStyleSheet(card_style)
        directories_layout = QVBoxLayout(directories_card)
        directories_layout.setSpacing(7)

        directories_header = QLabel('Директории')
        directories_header.setStyleSheet(header_style)
        directories_layout.addWidget(directories_header)

        # Стиль для полей ввода и кнопок
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
            self.memory_slider.setValue(settings['memory'])
        if 'minecraft_directory' in settings:
            self.directory_edit.setText(settings['minecraft_directory'])
        if 'mods_directory' in settings:
            self.mods_directory_edit.setText(settings['mods_directory'])

        # Принудительно обновляем стили
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def update_memory_label(self):
        self.memory_value_label.setText(f'{self.memory_slider.value()} ГБ')

    def choose_mods_directory(self):
        """Выбор директории для модов"""
        try:
            directory = QFileDialog.getExistingDirectory(
                self,
                'Выберите директорию для модов',
            )
            if directory:
                self.mods_directory_edit.setText(directory)
                MODS_DIR = directory
                # Сохраняем в настройках
                if self.parent_window:
                    self.parent_window.settings['mods_directory'] = directory
                    save_settings(self.parent_window.settings)
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
        """Открывает директорию с модами"""
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
        # Добавляем в layout настроек
        self.language_combo = QComboBox()
        self.language_combo.addItem('Русский', 'ru')
        self.language_combo.addItem('English', 'en')
        self.language_combo.currentIndexChanged.connect(self.change_language)

        # Добавляем в layout настроек
        language_layout = QHBoxLayout()
        language_label = QLabel('Язык:')
        language_label.setStyleSheet('color: #ffffff;')
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)

        # Добавляем в начало appearance_layout
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

        # Применяем новую тему
        self.parent_window.apply_dark_theme(
            new_theme == 'dark',
        )  # <- Исправлено на apply_dark_theme
        self.update_theme_button_icon()

        # Сохраняем выбор темы
        self.parent_window.settings['theme'] = new_theme
        save_settings(self.parent_window.settings)

    def update_theme_button_icon(self):
        """Обновляет иконку и текст кнопки в зависимости от текущей темы"""
        current_theme = getattr(self.parent_window, 'current_theme', 'dark')
        if current_theme == 'dark':
            self.theme_button.setIcon(QIcon(resource_path('assets/sun.png')))
            self.theme_button.setText(' Светлая тема')
        else:
            self.theme_button.setIcon(QIcon(resource_path('assets/moon.png')))
            self.theme_button.setText(' Тёмная тема')
        self.theme_button.setIconSize(QSize(24, 24))

    def update_logout_button_visibility(self):
        """Обновляет видимость кнопки выхода в зависимости от статуса авторизации"""
        if hasattr(self, 'ely_logout_button') and self.ely_logout_button:
            if hasattr(self.parent_window, 'ely_session') and self.parent_window.ely_session:
                self.ely_logout_button.setVisible(True)
            else:
                self.ely_logout_button.setVisible(False)
        # Принудительно обновляем layout
        self.layout().update()

    def choose_directory(self):
        try:
            directory = QFileDialog.getExistingDirectory(
                self,
                'Выберите директорию Minecraft',
            )
            if directory:
                self.directory_edit.setText(directory)
                MINECRAFT_DIR = directory
                SETTINGS_PATH = os.path.join(MINECRAFT_DIR, 'settings.json')
                LOG_FILE = os.path.join(MINECRAFT_DIR, 'launcher_log.txt')
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

    def closeEvent(self, event):
        # Сохраняем настройки через главное окно
        if self.parent_window:
            self.parent_window.settings = {
                'close_on_launch': self.close_on_launch_checkbox.isChecked(),
                'memory': self.memory_slider.value(),
                'minecraft_directory': self.directory_edit.text(),
                'mods_directory': self.mods_directory_edit.text(),
                # Убрали сохранение last_username здесь
            }
            save_settings(self.parent_window.settings)
