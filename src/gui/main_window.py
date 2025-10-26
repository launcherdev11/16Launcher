import json
import logging
import os
import platform
import random
import shutil
import subprocess
import sys
import traceback
import webbrowser
from typing import Any

import requests
from minecraft_launcher_lib.utils import get_version_list
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QCloseEvent, QIcon, QPalette, QPixmap
from PyQt5.QtWidgets import QGraphicsBlurEffect
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import constants

import ely
from config import AUTHLIB_JAR_PATH, MINECRAFT_DIR, SKINS_DIR
from ely_by_skin_manager import ElyBySkinManager
from ely_skin_manager import ElySkinManager
from translator import Translator
from util import (
    download_authlib_injector,
    generate_random_username,
    load_settings,
    resource_path,
    save_settings,
    save_ely_session,
    load_ely_session,
    clear_ely_session,
)
from .custom_line_edit import CustomLineEdit
from .threads.launch_thread import LaunchThread
from .widgets.mod_loader_tab import ModLoaderTab
from .widgets.modpack_tab import ModpackTab
from .widgets.mods_tab import ModsTab
from .widgets.settings_tab import SettingsTab
from .widgets.splash_screen import SplashScreen
from .widgets.console_widget import ConsoleWidget


def open_root_folder() -> None:
    folder = MINECRAFT_DIR

    if platform.system() == 'Windows':
        subprocess.Popen(f'explorer "{folder}"')
    elif platform.system() == 'Darwin':
        subprocess.Popen(['open', folder])
    else:
        subprocess.Popen(['xdg-open', folder])


def get_ely_skin(username: str) -> str | None:
    """Получает URL скина пользователя с Ely.by"""
    try:
        response = requests.get(
            f'https://skinsystem.ely.by/skins/{username}.png',
            allow_redirects=False,
        )
        if response.status_code == 200:
            return f'https://skinsystem.ely.by/skins/{username}.png'
        return None
    except Exception as e:
        logging.exception(f'Ошибка при получении скина: {e}')
        return None


class MainWindow(QMainWindow):
    __slots__ = (
        'console_widget',
        'ely_login_button',
        'ely_session',
        'fabric_tab',
        'forge_tab',
        'motd_label',
        'open_folder_button',
        'optifine_tab',
        'play_button',
        'quilt_tab',
        'random_name_button',
        'settings_button',
        'sidebar',
        'sidebar_container',
        'sidebar_layout',
        'splash',
        'start_progress_label',
        'support_button',
        'telegram_button',
        'toggle_sidebar_button',
        'username',
    )

    def __init__(self) -> None:
        self.console_widget = None
        super().__init__()

        # Загружаем настройки
        self.settings = load_settings()

        # Загружаем сохранённую сессию Ely.by
        self.ely_session = load_ely_session(self.settings)
        if self.ely_session:
            logging.info(f'✅ Автоматический вход в Ely.by: {self.ely_session.get("username")}')
        else:
            logging.info('ℹ️ Нет сохранённой сессии Ely.by')

        self.random_name_button = None
        self.ely_login_button = None
        self.open_folder_button = None
        self.start_progress_label = None
        self.start_progress = None
        self.motd_label = None
        self.username = None
        self.toggle_sidebar_button = None
        self.support_button = None
        self.telegram_button = None
        self.settings_button = None
        self.quilt_tab = None
        self.optifine_tab = None
        self.fabric_tab = None
        self.forge_tab = None
        self.play_button = None
        self.sidebar = None
        self.sidebar_layout = None
        self.sidebar_container = None
        self.splash = SplashScreen()
        self.splash.show()
        logging.debug('Инициализация основного окна')
        self.splash.update_progress(1, 'Инициализация основного окна...')
        super().__init__()

        self.splash.update_progress(2, 'Установка заголовка окна...')
        self.setWindowTitle('16Launcher 1.0.3')

        self.splash.update_progress(3, 'Установка размера окна...')
        self.setFixedSize(1280, 720)

        self.splash.update_progress(4, 'Установка размера окна...')
        self.setWindowIcon(QIcon(resource_path('assets/icon.ico')))

        logging.debug('Инициализация транслятора')
        self.splash.update_progress(5, 'Инициализация транслятора...')
        self.translator = Translator()

        logging.debug('Загружаем настройки')
        self.splash.update_progress(6, 'Загружаем настройки')
        self.settings = load_settings()

        self.splash.update_progress(7, 'Загружаем сессию через ely')
        self.setup_ely_auth()

        self.splash.update_progress(19, 'Устанавливаем никнейм')
        self.last_username = self.settings.get('last_username', '')

        self.splash.update_progress(20, 'Постанавливаем избранные версии')
        self.favorites = self.settings.get('favorites', [])

        self.splash.update_progress(21, 'Получаем последний версию')
        self.last_version = self.settings.get('last_version', '')

        self.splash.update_progress(22, 'Получаем последний загрузчик')
        self.last_loader = self.settings.get('last_loader', 'vanilla')

        logging.debug('Создаем UI элементы')
        self.splash.update_progress(23, 'Создаем UI элементы')
        self.launch_thread = LaunchThread(self)
        self.launch_thread.state_update_signal.connect(self.state_update)
        self.launch_thread.progress_update_signal.connect(self.update_progress)
        self.launch_thread.close_launcher_signal.connect(self.close_launcher)
        self.launch_thread.log_signal.connect(self.on_launch_log)

        logging.debug('Создаём основной контейнер')
        self.splash.update_progress(25, 'Создаём основной экран')
        self.main_container = QWidget(self)
        self.setCentralWidget(self.main_container)
        self.main_layout = QHBoxLayout(self.main_container)
        self.main_container.setLayout(self.main_layout)

        logging.debug('Создаём боковую панель')
        self.splash.update_progress(26, 'Создаём боковую панель')
        self.setup_sidebar()
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        self.tab_widget = QWidget()
        self.tab_layout = QVBoxLayout(self.tab_widget)
        self.tab_layout.setContentsMargins(15, 15, 15, 15)

        logging.debug('Создаём Game TAB')
        self.splash.update_progress(37, 'Создаём Game TAB')
        self.game_tab = QWidget()
        self.setup_game_tab()

        logging.debug('Создаём Mods TAB')
        self.splash.update_progress(38, 'Создаём Mods TAB')
        self.mods_tab = ModsTab(self)

        logging.debug('Создаём Modpacks TAB')
        self.splash.update_progress(39, 'Создаём Modpacks TAB')
        self.modpacks_tab = ModpackTab(self)

        logging.debug('Создаём меню вкладок')
        self.splash.update_progress(40, 'Создаём меню вкладок')
        self.tabs = QTabWidget()

        self.splash.update_progress(41, 'Добавляем вкладку `Запуск игры`')
        self.tabs.addTab(self.game_tab, 'Запуск игры')
        self.splash.update_progress(42, 'Добавляем вкладку `Моды`')
        self.tabs.addTab(self.mods_tab, 'Моды')
        self.splash.update_progress(43, 'Добавляем вкладку `Мои сборки`')
        self.tabs.addTab(self.modpacks_tab, 'Мои сборки')
        self.splash.update_progress(44, 'Добавляем вкладку `Мои сборки`')
        self.splash.update_progress(45, 'Добавляем меню вкладок на основную панель`')
        self.tab_layout.addWidget(self.tabs)

        logging.debug('Инициализируем вкладку загрузки')
        self.splash.update_progress(46, 'Инициализируем вкладку загрузки')
        self.setup_modloader_tabs()

        self.stacked_widget.addWidget(self.tab_widget)
        logging.debug('Инициализируем вкладку настроек')
        self.splash.update_progress(52, 'Инициализируем вкладку настроек')
        self.settings_tab = SettingsTab(self.translator, self)
        self.stacked_widget.addWidget(self.settings_tab)
        self.stacked_widget.setCurrentIndex(0)
        self.tabs.currentChanged.connect(self.handle_tab_changed)

        logging.debug('Инициализируем тёмную тему')
        self.splash.update_progress(53, 'Инициализируем тёмную тему')
        self.apply_dark_theme()

        self.splash.update_progress(54, 'Загрузка завершена')
        self.splash.close()
        logging.debug('Инициализация завершена')
        del self.splash


    def setup_modloader_tabs(self) -> None:
        # Существующие вкладки
        logging.debug('Создаём вкладку Forge')
        self.splash.update_progress(47, 'Создаём вкладку Forge')
        self.forge_tab = ModLoaderTab('forge')

        logging.debug('Создаём вкладку Fabric')
        self.splash.update_progress(48, 'Создаём вкладку Fabric')
        self.fabric_tab = ModLoaderTab('fabric')

        logging.debug('Создаём вкладку OptiFine')
        self.splash.update_progress(49, 'Создаём вкладку OptiFine')
        self.optifine_tab = ModLoaderTab('optifine')

        logging.debug('Создаём вкладку Quilt')
        self.splash.update_progress(50, 'Создаём вкладку Quilt')
        self.quilt_tab = ModLoaderTab('quilt')

        self.splash.update_progress(51, 'Добавляем вкладку на основную панель')
        self.tabs.addTab(self.quilt_tab, 'Quilt')
        self.tabs.addTab(self.forge_tab, 'Forge')
        self.tabs.addTab(self.fabric_tab, 'Fabric')
        self.tabs.addTab(self.optifine_tab, 'OptiFine')

    def setup_sidebar(self) -> None:
        """Создаёт боковую панель с возможностью сворачивания"""
        logging.debug('Создаём обёртку для панели и кнопки')
        self.splash.update_progress(27, 'Создаём панели и кнопки')
        self.sidebar_container = QWidget()
        self.sidebar_layout = QHBoxLayout(self.sidebar_container)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)

        logging.debug('Создаём боковую панель')
        self.splash.update_progress(28, 'Создаём боковую панель')
        self.sidebar = QFrame()
        self.sidebar.setFrameShape(QFrame.StyledPanel)
        self.sidebar.setFixedWidth(100)
        sidebar_content_layout = QVBoxLayout(self.sidebar)
        sidebar_content_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_content_layout.setSpacing(20)

        logging.debug('Создаём кнопку играть')
        self.splash.update_progress(29, 'Создаём кнопку играть')
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon(resource_path('assets/play64.png')))
        self.play_button.setIconSize(QSize(64, 64))
        self.play_button.setFixedSize(75, 75)
        self.play_button.setStyleSheet("""
               QPushButton {
                   border: none;
                   background-color: transparent;
                   font-size: 14px;
                   padding: 5px;
               }
               QPushButton:hover {
                   background-color: rgba(68, 68, 68, 0.8);
                   border-radius: 5px;
                   backdrop-filter: blur(10px);
               }
           """)
        self.play_button.clicked.connect(self.show_game_tab)
        sidebar_content_layout.addWidget(self.play_button, alignment=Qt.AlignCenter)

        logging.debug('Создаём кнопку настроек')
        self.splash.update_progress(30, 'Создаём кнопку настроек')
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(resource_path('assets/set64.png')))
        self.settings_button.setIconSize(QSize(64, 64))
        self.settings_button.setFixedSize(75, 75)
        self.settings_button.setStyleSheet(self.play_button.styleSheet())
        self.settings_button.clicked.connect(self.show_settings_tab)
        sidebar_content_layout.addWidget(self.settings_button, alignment=Qt.AlignCenter)

        sidebar_content_layout.addStretch()

        logging.debug('Создаём кнопку телеграмма')
        self.splash.update_progress(32, 'Создаём кнопку телеграмма')
        self.telegram_button = QPushButton()
        self.telegram_button.setIcon(QIcon(resource_path('assets/tg.png')))
        self.telegram_button.setIconSize(QSize(64, 64))
        self.telegram_button.setFixedSize(75, 75)
        self.telegram_button.setStyleSheet(self.play_button.styleSheet())
        self.telegram_button.clicked.connect(
            lambda: webbrowser.open('https://t.me/of16launcher'),
        )
        sidebar_content_layout.addWidget(self.telegram_button, alignment=Qt.AlignCenter)

        logging.debug('Создаём кнопку доната')
        self.splash.update_progress(33, 'Создаём кнопку доната')
        self.support_button = QPushButton()
        self.support_button.setIcon(QIcon(resource_path('assets/support64.png')))
        self.support_button.setIconSize(QSize(64, 64))
        self.support_button.setFixedSize(75, 75)
        self.support_button.setStyleSheet(self.play_button.styleSheet())
        self.support_button.clicked.connect(
            lambda: webbrowser.open('https://www.donationalerts.com/r/16steyy'),
        )
        sidebar_content_layout.addWidget(self.support_button, alignment=Qt.AlignCenter)

        logging.debug('Создаём Кнопку-свёртку')
        self.splash.update_progress(34, 'Создаём кнопку-свёртку')
        self.toggle_sidebar_button = QPushButton()
        self.toggle_sidebar_button.setIcon(QIcon(resource_path('assets/toggle.png')))
        self.toggle_sidebar_button.setIconSize(QSize(24, 24))
        self.toggle_sidebar_button.setFixedSize(30, 30)
        self.toggle_sidebar_button.setStyleSheet("""
               QPushButton {
                   background-color: rgba(68, 68, 68, 0.8);
                   color: white;
                   border: none;
                   border-top-right-radius: 5px;
                   border-bottom-right-radius: 5px;
                   backdrop-filter: blur(10px);
               }
               QPushButton:hover {
                   background-color: rgba(102, 102, 102, 0.9);
               }
           """)
        self.toggle_sidebar_button.clicked.connect(self.toggle_sidebar)

        logging.debug('Добавляем в основной контейнер')
        self.splash.update_progress(35, 'Добавляем в основной контейнер')
        self.sidebar_layout.addWidget(self.sidebar)
        self.sidebar_layout.addWidget(self.toggle_sidebar_button)

        self.main_layout.addWidget(self.sidebar_container)

    def setup_game_tab(self) -> None:
        # Создаем контейнер с полупрозрачным фоном
        self.game_tab.setStyleSheet("""
            QWidget {
                background-color: rgba(51, 51, 51, 0.7);
                border-radius: 15px;
                backdrop-filter: blur(20px);
            }
        """)
        
        layout = QVBoxLayout(self.game_tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.username = CustomLineEdit(self.game_tab)
        self.username.setPlaceholderText('Введите имя')
        self.username.setMinimumHeight(40)
        self.username.setText(self.last_username)

        self.username.setStyleSheet("""
            QLineEdit {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                padding: 10px 80px 10px 10px;
                border-radius: 10px;
                font-size: 14px;
                backdrop-filter: blur(10px);
            }
            QLineEdit:focus {
                border-color: rgba(161, 161, 161, 0.8);
                background-color: rgba(68, 68, 68, 0.9);
            }
        """)
        top_row.addWidget(self.username)

        self.random_name_button = QToolButton(self.username)
        self.random_name_button.setIcon(
            QIcon(resource_path('assets/random.png')),
        )  # Путь к вашей иконке
        self.random_name_button.setIconSize(QSize(45, 45))
        self.random_name_button.setCursor(Qt.PointingHandCursor)
        self.random_name_button.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QToolButton:hover {
                background-color: #666;
                border-radius: 3px;
            }
        """)
        self.random_name_button.setFixedSize(
            60,
            30,
        )  # Размер можно подобрать под вашу иконку
        self.random_name_button.setFixedSize(60, 30)
        self.random_name_button.clicked.connect(self.set_random_username)

        self.username.set_button(self.random_name_button)

        form_layout.addLayout(top_row)

        form_layout.addLayout(top_row)

        version_row = QHBoxLayout()
        version_row.setSpacing(10)

        # 1. Все/Избранные
        self.version_type_select = QComboBox(self.game_tab)
        self.version_type_select.setMinimumHeight(45)
        self.version_type_select.setFixedWidth(250)
        self.version_type_select.addItem('Все версии')
        self.version_type_select.addItem('Избранные')
        self.version_type_select.currentTextChanged.connect(self.update_version_list)
        self.version_type_select.setStyleSheet("""
            QComboBox {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                padding: 10px;
                border-radius: 10px;
                font-size: 14px;
                backdrop-filter: blur(10px);
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid rgba(85, 85, 85, 0.6);
                background: rgba(85, 85, 85, 0.8);
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        version_row.addWidget(self.version_type_select)

        # 2. Модлоадер
        self.loader_select = QComboBox(self.game_tab)
        self.loader_select.setMinimumHeight(45)
        self.loader_select.setFixedWidth(250)
        self.loader_select.addItem('Vanilla', 'vanilla')
        self.loader_select.addItem('Forge', 'forge')
        self.loader_select.addItem('Fabric', 'fabric')
        self.loader_select.addItem('OptiFine', 'optifine')
        self.loader_select.addItem('Quilt', 'quilt')
        self.loader_select.setStyleSheet(self.version_type_select.styleSheet())
        loader_index = self.loader_select.findData(self.last_loader)
        if loader_index >= 0:
            self.loader_select.setCurrentIndex(loader_index)
        version_row.addWidget(self.loader_select)

        # 3. Версия
        self.version_select = QComboBox(self.game_tab)
        self.version_select.setMinimumHeight(45)
        self.version_select.setFixedWidth(250)
        self.version_select.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.version_select.setStyleSheet(self.version_type_select.styleSheet())
        version_row.addWidget(self.version_select)

        # 4. Кнопка избранного
        self.favorite_button = QPushButton('★')
        self.favorite_button.setFixedSize(45, 45)
        self.favorite_button.setCheckable(True)
        self.favorite_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                border-radius: 10px;
                font-size: 18px;
                backdrop-filter: blur(10px);
            }
            QPushButton:hover {
                background-color: rgba(102, 102, 102, 0.9);
            }
            QPushButton:checked {
                color: gold;
                background-color: rgba(102, 102, 102, 0.9);
            }
        """)
        self.favorite_button.clicked.connect(self.toggle_favorite)
        version_row.addWidget(self.favorite_button)

        form_layout.addLayout(version_row)

        # Третья строка — Играть и Сменить скин
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.change_skin_button = QPushButton('Сменить скин (Ely.by)')
        self.change_skin_button.setMinimumHeight(50)
        self.change_skin_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                padding: 10px;
                border-radius: 10px;
                font-size: 14px;
                backdrop-filter: blur(10px);
            }
            QPushButton:hover {
                background-color: rgba(102, 102, 102, 0.9);
                transform: scale(1.05);
            }
        """)
        self.change_skin_button.clicked.connect(self.change_ely_skin)
        self.change_skin_button.setVisible(False)

        self.start_button = QPushButton('ИГРАТЬ')
        self.start_button.setMinimumHeight(50)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(40, 167, 69, 0.8);
                color: white;
                border: none;
                padding: 15px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                backdrop-filter: blur(8px);
            }
            QPushButton:hover {
                background-color: rgba(33, 136, 56, 0.9);
                transform: scale(1.05);
            }
            QPushButton:pressed {
                background-color: rgba(30, 120, 50, 0.95);
            }
        """)
        self.start_button.clicked.connect(self.launch_game)
        bottom_row.addWidget(self.start_button)

        self.ely_login_button = QPushButton('Войти с Ely.by')
        self.ely_login_button.setMinimumHeight(50)
        self.ely_login_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                padding: 10px;
                border-radius: 10px;
                font-size: 14px;
                backdrop-filter: blur(10px);
            }
            QPushButton:hover {
                background-color: rgba(102, 102, 102, 0.9);
                transform: scale(1.05);
            }
        """)
        self.ely_login_button.clicked.connect(self.handle_ely_login)

        bottom_row.addWidget(self.change_skin_button)
        bottom_row.addWidget(self.ely_login_button)

        # Кнопка "Открыть папку"
        self.open_folder_button = QPushButton()
        self.open_folder_button.setIcon(QIcon(resource_path('assets/folder.png')))
        self.open_folder_button.setToolTip('Открыть папку с игрой')
        self.open_folder_button.setIconSize(QSize(24, 24))
        self.open_folder_button.setCursor(Qt.PointingHandCursor)
        self.open_folder_button.setFixedSize(50, 50)
        self.open_folder_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(68, 68, 68, 0.8);
                border: 1px solid rgba(85, 85, 85, 0.6);
                border-radius: 10px;
                backdrop-filter: blur(10px);
            }
            QPushButton:hover {
                background-color: rgba(102, 102, 102, 0.9);
                transform: scale(1.05);
            }
        """)
        self.open_folder_button.clicked.connect(open_root_folder)
        bottom_row.addWidget(self.open_folder_button)

        # --- Сообщение дня ---
        self.motd_label = QLabel()
        self.motd_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.motd_label.setStyleSheet("""
            color: rgba(170, 170, 170, 0.7);
            font-style: italic;
            font-size: 14px;
            background: rgba(51, 51, 51, 0.3);
            padding: 10px;
            border-radius: 8px;
            backdrop-filter: blur(8px);
        """)
        layout.addWidget(self.motd_label)
        layout.addStretch()  # Добавляем растягивающееся пространство

        self.show_message_of_the_day()

        form_layout.addLayout(bottom_row)

        layout.addLayout(form_layout)

        self.start_progress_label = QLabel(self.game_tab)
        self.start_progress_label.setVisible(False)
        layout.addWidget(self.start_progress_label)

        self.start_progress = QProgressBar(self.game_tab)
        self.start_progress.setMinimumHeight(20)
        self.start_progress.setVisible(False)
        self.start_progress.setFormat('%p%')  # Показываем процент
        self.start_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(85, 85, 85, 0.6);
                background-color: rgba(51, 51, 51, 0.8);
                color: #f1f1f1;
                border-radius: 10px;
                text-align: center;
                backdrop-filter: blur(10px);
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: rgba(40, 167, 69, 0.9);
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.start_progress)

        # Добавляем консоль
        self.console_widget = ConsoleWidget(self.game_tab)
        self.console_widget.setVisible(False)  # По умолчанию скрыта
        layout.addWidget(self.console_widget)

        self.update_version_list()
        if self.last_version:
            index = self.version_select.findText(self.last_version)
            if index >= 0:
                self.version_select.setCurrentIndex(index)

        loader_index = self.loader_select.findData(self.last_loader)
        if loader_index >= 0:
            self.loader_select.setCurrentIndex(loader_index)
        
        # Обновляем UI если есть сохранённая сессия Ely.by
        if hasattr(self, 'ely_session') and self.ely_session:
            self.update_ely_ui(True)
            logging.debug(f'UI обновлён для сохранённой сессии: {self.ely_session.get("username")}')

    def setup_ely_auth(self) -> None:
        """Проверяет сохранённую сессию"""
        try:
            self.splash.update_progress(8, 'Проверяем авторизацию')
            logging.debug('Проверяем авторизацию')
            if ely.is_logged_in():
                logging.debug('Авторизация успешна')
                self.splash.update_progress(9, 'Авторизация успешна')
                logging.debug('Загружаем сессию')
                self.splash.update_progress(10, 'Загружаем сессию')
                self.ely_session = {
                    'username': ely.username(),
                    'uuid': ely.uuid(),
                    'token': ely.token(),
                }
                self.splash.update_progress(11, 'Устанавливаем никнейм')
                self.username.setText(self.ely_session['username'])
                self.splash.update_progress(12, 'Обновляем интерфейс')
                self.update_ely_ui(True)

                self.splash.update_progress(12, 'Проверяем текстуру скина')
                try:
                    logging.debug('Делаем запрос к API')
                    self.splash.update_progress(13, 'Делаем запрос к API')
                    texture_info = requests.get(
                        f'https://authserver.ely.by/session/profile/{self.ely_session["uuid"]}',
                        headers={
                            'Authorization': f'Bearer {self.ely_session["token"]}',
                        },
                    ).json()

                    if 'textures' in texture_info:
                        logging.debug('Текстура найдена')
                        logging.debug('Проверяем ссылку на скин')
                        self.splash.update_progress(14, 'Текстура найдена')
                        self.splash.update_progress(15, 'Проверяем ссылку на скин')
                        skin_url = texture_info['textures'].get('SKIN', {}).get('url')
                        if skin_url:
                            logging.debug('Ссылка найдена')
                            logging.debug('Делаем запрос на получение данных скина')
                            self.splash.update_progress(16, 'Ссылка найдена')
                            self.splash.update_progress(
                                17,
                                'Делаем запрос на получение данных скина',
                            )
                            skin_data = requests.get(skin_url).content
                            os.makedirs(SKINS_DIR, exist_ok=True)
                            with open(
                                os.path.join(
                                    SKINS_DIR,
                                    f'{self.ely_session["username"]}.png',
                                ),
                                'wb',
                            ) as f:
                                self.splash.update_progress(18, 'Устанавливаем скин')
                                f.write(skin_data)

                except Exception as e:
                    logging.exception(f'Ошибка проверки скина: {e}')

        except Exception as e:
            logging.exception(f'Ошибка загрузки сессии Ely.by: {e}')

    def retranslate_ui(self) -> None:
        """Обновляет все текстовые элементы интерфейса в соответствии с текущим языком"""
        self.setWindowTitle(self.translator.tr('window_title'))

        self.username.setPlaceholderText(self.translator.tr('username_placeholder'))
        self.random_name_button.setToolTip(
            self.translator.tr('generate_random_username'),
        )

        self.version_type_select.setItemText(0, self.translator.tr('all versions'))
        self.version_type_select.setItemText(1, self.translator.tr('favorites'))

        self.loader_select.setItemText(0, self.translator.tr('vanilla'))
        self.loader_select.setItemText(1, self.translator.tr('forge'))
        self.loader_select.setItemText(2, self.translator.tr('fabric'))
        self.loader_select.setItemText(3, self.translator.tr('optifine'))

        self.start_button.setText(self.translator.tr('launch_button'))
        self.ely_login_button.setText(self.translator.tr('ely_login_button'))

    def handle_tab_changed(self, index: int) -> None:
        """Обработчик смены вкладок"""

    def update_login_button_text(self) -> None:
        self.ely_login_button.setText(
            'Выйти из Ely.by' if hasattr(self, 'access_token') and self.access_token else 'Войти с Ely.by',
        )

    def show_game_tab(self) -> None:
        """Переключает на вкладку с игрой"""
        self.stacked_widget.setCurrentWidget(self.tab_widget)
        self.tabs.setCurrentIndex(0)

    def toggle_theme(self) -> None:
        current_theme = getattr(self, 'current_theme', 'dark')
        new_theme = 'light' if current_theme == 'dark' else 'dark'

        self.apply_theme(new_theme == 'dark')

        icon_path = 'assets/sun.png' if new_theme == 'light' else 'assets/moon.png'
        self.theme_button.setIcon(QIcon(resource_path(icon_path)))

        if hasattr(self.settings_tab, 'theme_button'):
            self.settings_tab.theme_button.setIcon(QIcon(resource_path(icon_path)))
            self.settings_tab.theme_button.setText(
                'Светлая тема' if new_theme == 'light' else 'Тёмная тема',
            )

        self.settings['theme'] = new_theme
        save_settings(self.settings)

    def show_settings_tab(self) -> None:
        """Переключает на вкладку с настройками"""
        self.stacked_widget.setCurrentWidget(self.settings_tab)

    def update_ely_ui(self, logged_in: bool) -> None:
        """Обновляет UI в зависимости от статуса авторизации"""
        if logged_in:
            self.ely_login_button.setVisible(False)
            self.change_skin_button.setVisible(True)
            self.change_skin_button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(40, 167, 69, 0.9);
                    color: white;
                    padding: 8px;
                    border-radius: 5px;
                    backdrop-filter: blur(10px);
                }
                QPushButton:hover {
                    background-color: rgba(33, 136, 56, 0.95);
                }
            """)
            self.change_skin_button.setText('Управление скином')
        else:
            self.ely_login_button.setVisible(True)
            self.change_skin_button.setVisible(False)

    def handle_ely_login(self) -> None:
        """Обработчик кнопки входа/выхода"""
        if hasattr(self, 'ely_session') and self.ely_session:
            self.ely_logout()
        else:
            self.ely_login()
        # Обновляем кнопку в настройках
        if hasattr(self.settings_tab, 'update_logout_button_visibility'):
            self.settings_tab.update_logout_button_visibility()

    def ely_login(self) -> None:
        """Диалог ввода логина/пароля"""
        email, ok = QInputDialog.getText(
            self,
            'Вход',
            'Введите email Ely.by:',
            QLineEdit.Normal,
            '',
        )
        if not ok or not email:
            return

        password, ok = QInputDialog.getText(
            self,
            'Вход',
            'Введите пароль:',
            QLineEdit.Password,
            '',
        )
        if not ok or not password:
            return

        try:
            self.ely_session = ely.auth_password(email, password)
            
            # Сохраняем через старый механизм (для совместимости)
            ely.write_login_data(
                {
                    'username': self.ely_session['username'],
                    'uuid': self.ely_session['uuid'],
                    'token': self.ely_session['token'],
                    'logged_in': True,
                }
            )
            
            # Сохраняем через новый механизм (в settings.json)
            save_ely_session(self.settings, self.ely_session)
            
            self.update_ely_ui(True)
            self.username.setText(self.ely_session['username'])
            QMessageBox.information(self, 'Успешно', 'Авторизация прошла успешно!')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def start_device_auth(self, dialog: QInputDialog) -> None:
        """Запуск авторизации через device code"""
        dialog.close()
        try:
            self.ely_session = ely.auth_device_code()
            
            # Сохраняем через оба механизма
            ely.write_login_data(
                {
                    'username': self.ely_session['username'],
                    'uuid': self.ely_session['uuid'],
                    'token': self.ely_session['token'],
                    'logged_in': True,
                }
            )
            save_ely_session(self.settings, self.ely_session)
            
            self.update_ely_ui(True)
            self.username.setText(self.ely_session['username'])
            QMessageBox.information(
                self,
                'Успешно',
                f'Вы вошли как {self.ely_session["username"]}',
            )
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def start_credentials_auth(self, dialog: QInputDialog) -> None:
        """Запуск авторизации по логину/паролю"""
        dialog.close()
        email, ok = QInputDialog.getText(self, 'Вход', 'Введите email Ely.by:')
        if not (ok or email):
            return

        password, ok = QInputDialog.getText(
            self,
            'Вход',
            'Введите пароль:',
            QLineEdit.Password,
        )
        if not (ok or password):
            return

        try:
            self.ely_session = ely.auth(email, password)
            
            # Сохраняем через оба механизма
            ely.write_login_data(
                {
                    'username': self.ely_session['username'],
                    'uuid': self.ely_session['uuid'],
                    'token': self.ely_session['token'],
                    'logged_in': True,
                }
            )
            save_ely_session(self.settings, self.ely_session)
            
            self.update_ely_ui(True)
            self.username.setText(self.ely_session['username'])
            QMessageBox.information(
                self,
                'Успешно',
                f'Вы вошли как {self.ely_session["username"]}',
            )
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def ely_logout(self) -> None:
        """Выход из аккаунта Ely.by"""
        try:
            # Очищаем через старый механизм
            ely.logout()
            
            # Очищаем через новый механизм
            self.ely_session = None
            clear_ely_session(self.settings)
            
            # Обновляем UI
            self.update_ely_ui(False)
            self.username.setText('')
            if hasattr(self, 'settings_tab'):
                self.settings_tab.update_logout_button_visibility()
            
            QMessageBox.information(self, 'Выход', 'Вы вышли из аккаунта Ely.by')
            logging.info('Выход из Ely.by выполнен')
        except Exception as e:
            logging.exception(f'Ошибка при выходе из Ely.by: {e}')

    def open_support_tab(self) -> None:
        support_tab = QWidget()
        layout = QVBoxLayout(support_tab)

        text = QLabel(
            'Наш лаунчер абсолютно бесплатный и безопасный, если тебе нравится лаунчер, его функции, дизайн,'
            '\nты можешь поддержать разработчика ❤',
        )
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        layout.addWidget(text)
        text.setFixedSize(700, 900)

        # Кнопка "Поддержать"
        donate_button = QPushButton('Поддержать')
        donate_button.setFixedSize(200, 50)
        donate_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 16px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        donate_button.clicked.connect(
            lambda: webbrowser.open('https://www.donationalerts.com/r/16steyy'),
        )
        layout.addWidget(donate_button, alignment=Qt.AlignCenter)

        layout.addStretch()

        self.stacked_widget.addWidget(support_tab)
        self.stacked_widget.setCurrentWidget(support_tab)

    def change_ely_skin(self) -> None:
        """Открывает диалог управления скином для Ely.by"""
        if not hasattr(self, 'ely_session') or not self.ely_session:
            QMessageBox.warning(self, 'Ошибка', 'Сначала войдите в Ely.by!')
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('Управление скином')
        dialog.setFixedSize(400, 250)

        layout = QVBoxLayout()

        # Кнопка загрузки нового скина
        upload_btn = QPushButton('Загрузить новый скин')
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        upload_btn.clicked.connect(lambda: self.upload_new_skin(dialog))
        layout.addWidget(upload_btn)

        # Кнопка сброса скина
        reset_btn = QPushButton('Сбросить скин на стандартный')
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        reset_btn.clicked.connect(lambda: self.reset_ely_skin(dialog))
        layout.addWidget(reset_btn)

        # Кнопка открытия страницы управления
        manage_btn = QPushButton('Открыть страницу управления')
        manage_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
        """)
        manage_btn.clicked.connect(
            lambda: webbrowser.open(
                f'https://ely.by/skins?username={self.ely_session["username"]}',
            ),
        )
        layout.addWidget(manage_btn)

        # Кнопка закрытия
        close_btn = QPushButton('Закрыть')
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec_()

    def upload_new_skin(self, parent_dialog: QInputDialog) -> None:
        """Загружает новый скин на Ely.by"""
        parent_dialog.close()

        # Диалог выбора файла
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Выберите PNG-файл скина (64x64 или 64x32)',
            '',
            'PNG Images (*.png)',
        )

        if not file_path:
            return  # Пользователь отменил выбор

        # Диалог выбора типа модели
        model_type, ok = QInputDialog.getItem(
            self,
            'Тип модели',
            'Выберите тип модели:',
            ['classic', 'slim'],
            0,
            False,
        )

        if not ok:
            return

        try:
            # Загружаем скин
            success, message = ElySkinManager.upload_skin(
                file_path,
                self.ely_session['token'],
                model_type,
            )

            if success:
                # Скачиваем обновлённый скин для отображения в лаунчере
                skin_url = ElySkinManager.get_skin_url(self.ely_session['username'])
                if skin_url:
                    skin_data = requests.get(skin_url).content
                    skin_path = os.path.join(SKINS_DIR, f'{self.username.text()}.png')

                    os.makedirs(SKINS_DIR, exist_ok=True)
                    with open(skin_path, 'wb') as f:
                        f.write(skin_data)

                    QMessageBox.information(self, 'Успех', message)
                else:
                    QMessageBox.warning(
                        self,
                        'Ошибка',
                        'Не удалось получить новый скин',
                    )
            else:
                QMessageBox.critical(self, 'Ошибка', message)

        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def reset_ely_skin(self, parent_dialog: QInputDialog) -> None:
        """Сбрасывает скин на стандартный"""
        parent_dialog.close()

        try:
            success, message = ElySkinManager.reset_skin(self.ely_session['token'])
            if success:
                # Удаляем локальную копию скина
                skin_path = os.path.join(SKINS_DIR, f'{self.username.text()}.png')
                if os.path.exists(skin_path):
                    os.remove(skin_path)

                QMessageBox.information(self, 'Успех', message)
            else:
                QMessageBox.critical(self, 'Ошибка', message)
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def update_version_list(self) -> None:
        """Обновляет список версий в зависимости от выбранного типа"""
        current_text = self.version_select.currentText()
        self.version_select.clear()

        show_only_favorites = self.version_type_select.currentText() == 'Избранные'
        show_snapshots = self.settings.get('show_snapshots', False)

        for v in get_version_list():
            if v['type'] == 'release' or (show_snapshots and v['type'] == 'snapshot'):
                version_id = v['id']
                if not show_only_favorites or version_id in self.favorites:
                    if v['type'] == 'snapshot':
                        display_text = f"{version_id} (snapshot)"
                    else:
                        display_text = version_id
                    self.version_select.addItem(display_text, version_id)

        # Восстанавливаем выбранную версию
        if current_text:
            # Ищем по отображаемому тексту
            index = self.version_select.findText(current_text)
            if index >= 0:
                self.version_select.setCurrentIndex(index)
            else:
                # Ищем по ID версии (для совместимости со старыми настройками)
                current_version_id = current_text.replace(' (snapshot)', '')
                for i in range(self.version_select.count()):
                    if self.version_select.itemData(i) == current_version_id:
                        self.version_select.setCurrentIndex(i)
                        break

        self.update_favorite_button()

    def get_selected_version_id(self) -> str:
        """Извлекает ID версии из выбранного элемента комбобокса"""
        current_index = self.version_select.currentIndex()
        if current_index >= 0:
            version_id = self.version_select.currentData()
            if version_id:
                return version_id
        
        current_text = self.version_select.currentText()
        if current_text:
            return current_text.replace(' (snapshot)', '')
        return ''

    def toggle_sidebar(self) -> None:
        is_visible = self.sidebar.isVisible()
        self.sidebar.setVisible(not is_visible)
        self.toggle_sidebar_button.setIcon(
            QIcon(
                resource_path(
                    'assets/toggle_open.png' if is_visible else 'assets/toggle_close.png',
                ),
            ),
        )

    def toggle_favorite(self) -> None:
        """Добавляет или удаляет версию из избранного"""
        version = self.get_selected_version_id()
        if not version:
            return

        if version in self.favorites:
            self.favorites.remove(version)
        else:
            self.favorites.append(version)

        self.settings['favorites'] = self.favorites
        save_settings(self.settings)

        self.update_favorite_button()
        if self.version_type_select.currentText() == 'Избранные':
            self.update_version_list()

    def update_favorite_button(self) -> None:
        version = self.get_selected_version_id()
        if not version:
            self.favorite_button.setChecked(False)
            self.favorite_button.setEnabled(False)
            return

        self.favorite_button.setEnabled(True)
        self.favorite_button.setChecked(version in self.favorites)
        self.favorite_button.setStyleSheet(
            'QPushButton {color: %s;}' % ('gold' if version in self.favorites else 'gray'),
        )

    def get_selected_memory(self) -> None:
        """Возвращает выбранное количество памяти в мегабайтах"""
        return self.settings_tab.memory_slider.value() * 1024 
    def load_skin(self) -> None:
        source_dialog = QDialog(self)
        source_dialog.setWindowTitle('Выберите источник скина')
        source_dialog.setFixedSize(300, 200)

        layout = QVBoxLayout()

        label = QLabel('Откуда загрузить скин?')
        layout.addWidget(label)

        local_button = QPushButton('С компьютера')
        layout.addWidget(local_button)

        elyby_button = QPushButton('С Ely.by')
        layout.addWidget(elyby_button)

        source_dialog.setLayout(layout)

        def load_from_local():
            source_dialog.close()
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                'Выбери PNG-файл скина',
                '',
                'PNG файлы (*.png)',
            )
            if file_path:
                try:
                    os.makedirs(SKINS_DIR, exist_ok=True)
                    dest_path = os.path.join(
                        SKINS_DIR,
                        f'{self.username.text().strip()}.png',
                    )
                    shutil.copy(file_path, dest_path)
                    QMessageBox.information(
                        self,
                        'Скин загружен',
                        'Скин успешно загружен!',
                    )
                except Exception as e:
                    logging.exception(f'Ошибка загрузки скина: {e}')
                    QMessageBox.critical(
                        self,
                        'Ошибка',
                        f'Не удалось загрузить скин: {e}',
                    )

        def load_from_elyby():
            source_dialog.close()
            username = self.username.text().strip()
            if not username:
                QMessageBox.warning(self, 'Ошибка', 'Введите имя игрока!')
                return

            if ElyBySkinManager.download_skin(username):
                QMessageBox.information(
                    self,
                    'Скин загружен',
                    'Скин успешно загружен с Ely.by!',
                )
            else:
                ElyBySkinManager.authorize_and_get_skin(self, username)

        local_button.clicked.connect(load_from_local)
        elyby_button.clicked.connect(load_from_elyby)

        source_dialog.exec_()

    def load_user_data(self) -> None:
        if os.path.exists(self.user_data_path):
            try:
                with open(self.user_data_path, encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.info('⚠️ Ошибка загрузки user_data:', e)
        return {'launch_count': 0, 'achievements': []}

    def save_user_data(self) -> None:
        try:
            with open(self.user_data_path, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, indent=4)
        except Exception as e:
            logging.info('⚠️ Ошибка сохранения user_data:', e)

    def increment_launch_count(self) -> None:
        self.user_data['launch_count'] += 1
        count = self.user_data['launch_count']
        logging.info(f'🚀 Запуск №{count}')

        # Проверка достижений
        if count >= 1 and 'first_launch' not in self.user_data['achievements']:
            self.user_data['achievements'].append('first_launch')
        if count >= 5 and 'five_launches' not in self.user_data['achievements']:
            self.user_data['achievements'].append('five_launches')

        self.save_user_data()

    def set_random_username(self) -> None:
        self.username.setText(generate_random_username())

    def apply_dark_theme(self, dark_theme: bool = True) -> None:
        dark_theme_css = """
        QMainWindow {
            background-color: #606060;
        }
        QWidget {
            background-color: transparent;
            color: #f1f1f1;
        }
        QLineEdit {
            background-color: rgba(68, 68, 68, 0.8);
            color: #f1f1f1;
            border: 1px solid rgba(85, 85, 85, 0.6);
            padding: 10px 30px 10px 10px;
            border-radius: 10px;
            font-size: 14px;
            backdrop-filter: blur(10px);
        }
        QLineEdit:focus {
            border-color: rgba(161, 161, 161, 0.8);
            background-color: rgba(68, 68, 68, 0.9);
        }
        QPushButton {
            background-color: rgba(68, 68, 68, 0.8);
            color: #f1f1f1;
            border: 1px solid rgba(85, 85, 85, 0.6);
            padding: 10px;
            border-radius: 10px;
            font-size: 14px;
            backdrop-filter: blur(10px);
        }
        QPushButton:hover {
            background-color: rgba(102, 102, 102, 0.9);
            transform: scale(1.05);
        }
        QPushButton:focus {
            border-color: rgba(161, 161, 161, 0.8);
        }
        QToolButton {
            background-color: transparent;
            border: none;
            padding: 0;
        }
        QToolButton:hover {
            background-color: #666;
            border-radius: 3px;
        }
        QComboBox {
            background-color: rgba(68, 68, 68, 0.8);
            color: #f1f1f1;
            border: 1px solid rgba(85, 85, 85, 0.6);
            padding: 10px;
            border-radius: 10px;
            font-size: 14px;
            backdrop-filter: blur(10px);
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border-left: 1px solid rgba(85, 85, 85, 0.6);
            background: rgba(85, 85, 85, 0.8);
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
        }
        QComboBox QAbstractItemView {
            background-color: rgba(51, 51, 51, 0.95);
            color: #f1f1f1;
            selection-background-color: rgba(85, 85, 85, 0.8);
            border: 1px solid rgba(68, 68, 68, 0.6);
            padding: 5px;
            outline: none;
            backdrop-filter: blur(15px);
        }
        QComboBox QAbstractItemView::item {
            padding: 6px 10px;
            border: none;
            outline: none;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #555;
            border: none;
            outline: none;
        }
        /* Scrollbar inside QComboBox popup (dark) */
        QComboBox QAbstractItemView QScrollBar:vertical {
            border: none;
            background: #2e2e2e;
            width: 10px;
            margin: 0px;
            border-radius: 5px;
        }
        QComboBox QAbstractItemView QScrollBar::handle:vertical {
            background: #555555;
            min-height: 18px;
            border-radius: 5px;
        }
        QComboBox QAbstractItemView QScrollBar::handle:vertical:hover {
            background: #777777;
        }
        QComboBox QAbstractItemView QScrollBar::add-line:vertical,
        QComboBox QAbstractItemView QScrollBar::sub-line:vertical {
            height: 0px;
            background: transparent;
        }
        QComboBox QAbstractItemView QScrollBar::add-page:vertical,
        QComboBox QAbstractItemView QScrollBar::sub-page:vertical {
            background: #2e2e2e; /* track color to remove white gap */
        }
        QProgressBar {
            border: 1px solid #555555;
            background-color: #333333;
            color: #f1f1f1;
        }
        QSlider::groove:horizontal {
            background: #383838;
            height: 6px;
            border-radius: 3px;
        }

        QSlider::sub-page:horizontal {
            background: #505050;
            border-radius: 3px;
        }

        QSlider::add-page:horizontal {
            background: #282828;
            border-radius: 3px;
        }

        QSlider::handle:horizontal {
            background: #ffffff;
            width: 16px;
            height: 16px;
            margin: -4px 0;
            border-radius: 8px;
            border: 2px solid #3a7bd5;
        }

        QSlider::handle:horizontal:hover {
            background: #f0f0f0;
        }
        QTabWidget::pane {
            border: 1px solid rgba(68, 68, 68, 0.6);
            background: rgba(51, 51, 51, 0.85);
            backdrop-filter: blur(15px);
        }
        QTabBar::tab {
            background: rgba(68, 68, 68, 0.8);
            color: #fff;
            padding: 8px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            backdrop-filter: blur(10px);
        }
        QTabBar::tab:selected {
            background: rgba(85, 85, 85, 0.9);
            border-color: rgba(102, 102, 102, 0.8);
        }
        QFrame {
            background-color: rgba(37, 37, 37, 0.85);
            border-right: 1px solid rgba(68, 68, 68, 0.6);
            backdrop-filter: blur(15px);
        }
        /* Unified scrollbars (dark) */
        QScrollBar:vertical {
            border: none;
            background: #2e2e2e;
            width: 12px;
            margin: 0px 0px 0px 0px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: #777777;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
            background: transparent;
            border: none;
        }
        QScrollBar:horizontal {
            border: none;
            background: #2e2e2e;
            height: 12px;
            margin: 0px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal {
            background: #555555;
            min-width: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #777777;
        }
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {
            width: 0px;
            background: transparent;
            border: none;
        }
        /* Remove white gaps on page areas */
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical,
        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {
            background: #2e2e2e;
        }
        """

        vertical_slider_style = """
        QSlider::groove:vertical {
            background: #383838;
            width: 8px;
            border-radius: 4px;
            margin: 4px 0;
        }

        QSlider::sub-page:vertical {
            background: qlineargradient(x1:0, y1:1, x2:0, y2:0,
                stop:0 #3a7bd5, stop:1 #00d2ff);
            border-radius: 4px;
        }

        QSlider::handle:vertical {
            background: #ffffff;
            width: 20px;
            height: 20px;
            margin: 0 -6px;
            border-radius: 10px;
            border: 2px solid #3a7bd5;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
    """

        light_theme_css = """
        QMainWindow {
            background-color: transparent;
        }
        QWidget {
            background-color: transparent;
            color: #333333;
        }
        QLineEdit {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #cccccc;
            padding: 10px 30px 10px 10px;
            border-radius: 10px;
            font-size: 14px;
        }
        QLineEdit:focus {
            border-color: #66afe9;
        }
        QPushButton {
            background-color: #e0e0e0;
            color: #333333;
            border: 1px solid #cccccc;
            padding: 10px;
            border-radius: 10px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
            transform: scale(1.1);
        }
        QPushButton:focus {
            border-color: #66afe9;
        }
        QToolButton {
            background-color: transparent;
            border: none;
            padding: 0;
        }
        QToolButton:hover {
            background-color: #d0d0d0;
            border-radius: 3px;
        }
        QComboBox {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #cccccc;
            padding: 10px;
            border-radius: 10px;
            font-size: 14px;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border-left: 1px solid #cccccc;
            background: #e0e0e0;
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
        }
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #333333;
            selection-background-color: #e0e0e0;
            border: 1px solid #cccccc;
            padding: 5px;
            outline: none;
        }
        QComboBox QAbstractItemView::item {
            padding: 6px 10px;
            border: none;
            outline: none;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #e0e0e0;
            border: none;
            outline: none;
        }
        /* Scrollbar inside QComboBox popup (light) */
        QComboBox QAbstractItemView QScrollBar:vertical {
            border: none;
            background: #f5f5f5;
            width: 10px;
            margin: 0px;
            border-radius: 5px;
        }
        QComboBox QAbstractItemView QScrollBar::handle:vertical {
            background: #c0c0c0;
            min-height: 18px;
            border-radius: 5px;
        }
        QComboBox QAbstractItemView QScrollBar::handle:vertical:hover {
            background: #a0a0a0;
        }
        QComboBox QAbstractItemView QScrollBar::add-line:vertical,
        QComboBox QAbstractItemView QScrollBar::sub-line:vertical {
            height: 0px;
            background: transparent;
        }
        QComboBox QAbstractItemView QScrollBar::add-page:vertical,
        QComboBox QAbstractItemView QScrollBar::sub-page:vertical {
            background: #f5f5f5; /* track color to remove white gap */
        }
        QProgressBar {
            border: 1px solid #cccccc;
            background-color: #ffffff;
            color: #333333;
        }
        QSlider::groove:horizontal {
            background: #e0e0e0;
            height: 6px;
            border-radius: 3px;
            border: 1px solid #cccccc;
        }
        QSlider::handle:horizontal {
            background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                    stop:0 #f0f0f0, stop:0.5 #d0d0d0, stop:1 #f0f0f0);
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
            border: 1px solid #aaaaaa;
        }
        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #3a7bd5, stop:1 #00d2ff);
            border-radius: 3px;
        }
        QTabWidget::pane {
            border: 1px solid #cccccc;
            background: #ffffff;
        }
        QTabBar::tab {
            background: #e0e0e0;
            color: #333333;
            padding: 8px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            border-color: #cccccc;
        }
        QFrame {
            background-color: #f0f0f0;
            border-right: 1px solid #cccccc;
        }
        QScrollBar:vertical {
            border: none;
            background: #f5f5f5;
            width: 12px;
            margin: 0px 0px 0px 0px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #c0c0c0;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: #a0a0a0;
        }
        """

        # Применяем выбранную тему
        self.setStyleSheet(dark_theme_css if dark_theme else light_theme_css)
        self.current_theme = 'dark' if dark_theme else 'light'

        # Меняем иконки в зависимости от темы
        icon_suffix = '' if dark_theme else '_dark'

        # Обновляем иконки кнопок, если они существуют
        if hasattr(self, 'theme_button'):
            self.theme_button.setIcon(
                QIcon(resource_path(f'assets/sun{icon_suffix}.png')),
            )
        if hasattr(self, 'settings_button'):
            self.settings_button.setIcon(
                QIcon(resource_path(f'assets/set64{icon_suffix}.png')),
            )
        if hasattr(self, 'telegram_button'):
            self.telegram_button.setIcon(
                QIcon(resource_path(f'assets/tg{icon_suffix}.png')),
            )
        if hasattr(self, 'support_button'):
            self.support_button.setIcon(
                QIcon(resource_path(f'assets/support64{icon_suffix}.png')),
            )
        if hasattr(self, 'play_button'):
            self.play_button.setIcon(
                QIcon(resource_path(f'assets/play64{icon_suffix}.png')),
            )
        if hasattr(self, 'toggle_sidebar_button'):
            is_visible = self.sidebar.isVisible()
            icon_name = 'toggle_open' if is_visible else 'toggle_close'
            self.toggle_sidebar_button.setIcon(
                QIcon(resource_path(f'assets/{icon_name}{icon_suffix}.png')),
            )
        if hasattr(self, 'random_name_button'):
            self.random_name_button.setIcon(
                QIcon(resource_path(f'assets/random{icon_suffix}.png')),
            )
        if hasattr(self, 'open_folder_button'):
            self.open_folder_button.setIcon(
                QIcon(resource_path(f'assets/folder{icon_suffix}.png')),
            )
        if hasattr(self, 'favorite_button'):
            # Для кнопки избранного используем цвет вместо иконки
            version = self.get_selected_version_id()
            if version:
                self.favorite_button.setStyleSheet(
                    'QPushButton {color: %s;}' % ('gold' if version in self.favorites else 'gray'),
                )
        if hasattr(self, 'ely_button'):
            # Для кнопки Ely.by используем стандартную иконку
            self.ely_button.setIcon(QIcon(resource_path('assets/account.png')))
        if hasattr(self, 'skin_button'):
            # Для кнопки скина используем стандартную иконку
            self.skin_button.setIcon(QIcon(resource_path('assets/change_name.png')))

        # Обновляем иконки в настройках
        if hasattr(self, 'settings_tab'):
            if hasattr(self.settings_tab, 'theme_button'):
                self.settings_tab.theme_button.setIcon(
                    QIcon(resource_path(f'assets/sun{icon_suffix}.png')),
                )

        # Обновляем цвет MOTD-сообщения
        if hasattr(self, 'motd_label'):
            color = '#aaaaaa' if dark_theme else '#666666'
            self.motd_label.setStyleSheet(f"""
                color: {color};
                font-style: italic;
                font-size: 14px;
                background: transparent;
                padding: 5px;
            """)

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Переопределяем метод закрытия окна для сохранения настроек"""
        # Сохраняем текущий выбор
        current_version = self.get_selected_version_id()
        if current_version:
            self.settings['last_version'] = current_version
            self.settings['last_loader'] = self.loader_select.currentData()
            self.settings['show_snapshots'] = self.settings_tab.show_snapshots_checkbox.isChecked()

        self.settings['last_username'] = self.username.text().strip()
        
        # Сохраняем настройки консоли
        if hasattr(self.settings_tab, 'show_console_checkbox'):
            self.settings['show_console'] = self.settings_tab.show_console_checkbox.isChecked()
        if hasattr(self.settings_tab, 'hide_console_checkbox'):
            self.settings['hide_console_after_launch'] = self.settings_tab.hide_console_checkbox.isChecked()
            
        save_settings(self.settings)
        event.accept()

    def close_launcher(self) -> None:
        """Закрывает лаунчер после запуска игры"""
        self.close()

    def launch_game(self) -> None:
        try:
            logging.info('[LAUNCHER] Starting game launch process...')

            username = self.username.text().strip()
            if not username:
                QMessageBox.warning(self, 'Ошибка', 'Введите имя игрока!')
                return

            version = self.get_selected_version_id()
            loader_type = self.loader_select.currentData()
            memory_mb = self.get_selected_memory()
            close_on_launch = self.settings_tab.close_on_launch_checkbox.isChecked()

            logging.info(
                f'[LAUNCHER] Launch parameters: '
                f'User: {username}, '
                f'Version: {version}, '
                f'Loader: {loader_type}, '
                f'Memory: {memory_mb}MB, '
                f'Close on launch: {close_on_launch}',
            )

            # Handle Ely.by session
            if not hasattr(self, 'ely_session'):
                self.ely_session = None
                logging.info('[LAUNCHER] No Ely.by session found')

            # Prepare skin
            skin_path = os.path.join(SKINS_DIR, f'{username}.png')
            if os.path.exists(skin_path):
                logging.info('[LAUNCHER] Found skin, copying...')
                assets_dir = os.path.join(MINECRAFT_DIR, 'assets', 'skins')
                os.makedirs(assets_dir, exist_ok=True)
                shutil.copy(skin_path, os.path.join(assets_dir, f'{username}.png'))

            # Handle authlib for Ely.by
            if hasattr(self, 'ely_session') and self.ely_session:
                logging.info('[LAUNCHER] Ely.by session detected, checking authlib...')
                if not os.path.exists(AUTHLIB_JAR_PATH):
                    logging.info('[LAUNCHER] Downloading authlib-injector...')
                    if not download_authlib_injector():
                        QMessageBox.critical(
                            self,
                            'Ошибка',
                            'Не удалось загрузить Authlib Injector',
                        )
                        return

            # Save last used settings
            self.settings['last_version'] = version
            self.settings['last_loader'] = loader_type
            save_settings(self.settings)

            # Show progress UI
            self.start_progress_label.setText('Подготовка к запуску...')
            self.start_progress_label.setVisible(True)
            self.start_progress.setVisible(True)
            QApplication.processEvents()  # Force UI update

            logging.info('[LAUNCHER] Starting launch thread...')
            self.launch_thread.launch_setup(
                version,
                username,
                loader_type,
                memory_mb,
                close_on_launch,
            )
            self.launch_thread.start()

        except Exception as e:
            logging.exception(f'[ERROR] Launch failed: {e!s}')
            logging.exception(f'Game launch failed: {traceback.format_exc()}')
            QMessageBox.critical(
                self,
                'Ошибка запуска',
                f'Не удалось запустить игру: {e!s}',
            )

    def update_progress(self, current: int, total: int, text: str) -> None:
        self.start_progress.setMaximum(total)
        self.start_progress.setValue(current)
        if text:
            self.start_progress_label.setText(text)

    def state_update(self, is_running: bool) -> None:
        if is_running:
            self.start_button.setEnabled(False)
            # Показать консоль при запуске, если включена в настройках
            if hasattr(self.settings_tab, 'show_console_checkbox') and self.settings_tab.show_console_checkbox.isChecked():
                self.console_widget.show_console()
        else:
            self.start_button.setEnabled(True)
            self.start_progress_label.setVisible(False)
            self.start_progress.setVisible(False)
            # Скрыть консоль после запуска, если включена соответствующая настройка
            if (hasattr(self.settings_tab, 'hide_console_checkbox') and 
                self.settings_tab.hide_console_checkbox.isChecked() and
                hasattr(self.settings_tab, 'show_console_checkbox') and 
                self.settings_tab.show_console_checkbox.isChecked()):
                self.console_widget.hide_console()

    def on_launch_log(self, message: str) -> None:
        """Обработчик логов от launch_thread"""
        if self.console_widget and self.console_widget.isVisible():
            self.console_widget.add_log_with_color(message)

    def show_message_of_the_day(self) -> None:
        if hasattr(self, 'motd_label') and self.settings.get('show_motd', True):
            message = random.choice(constants.MOTD_MESSAGES)
            self.motd_label.setText(f'💬 <i>{message}</i>')
        else:
            self.motd_label.clear()