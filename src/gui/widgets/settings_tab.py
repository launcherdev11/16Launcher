import logging
import os
import subprocess

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
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

    # Блокирующие колесо мыши варианты виджетов
    class _NoWheelSlider(QSlider):
        def wheelEvent(self, event):  # type: ignore[override]
            event.ignore()
            return

    class _NoWheelCombo(QComboBox):
        def wheelEvent(self, event):  # type: ignore[override]
            event.ignore()
            return

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

        # Временно скрываем категорию "Внешний вид"
        appearance_card.setVisible(False)

        #консоль

        settings_layout.addWidget(appearance_card)

        # Java настройки
        java_card = QWidget()
        java_card.setStyleSheet(card_style)
        java_layout = QVBoxLayout(java_card)
        java_layout.setSpacing(15)

        java_header = QLabel('Настройки Java')
        java_header.setStyleSheet(header_style)
        java_layout.addWidget(java_header)

        # Выбор Java: рекоменд., текущая, пользовательская
        self.java_radio_recommended = QRadioButton('Рекомендуемая')
        self.java_radio_current = QRadioButton('Текущая (из PATH)')
        self.java_radio_custom = QRadioButton('Пользовательская')
        for rb in (self.java_radio_recommended, self.java_radio_current, self.java_radio_custom):
            rb.setStyleSheet('color: #ffffff; font-size: 15px;')
        radios_row = QHBoxLayout()
        radios_row.addWidget(self.java_radio_recommended)
        radios_row.addWidget(self.java_radio_current)
        radios_row.addWidget(self.java_radio_custom)
        java_layout.addLayout(radios_row)

        # Путь к Java + кнопки
        java_path_row = QHBoxLayout()
        java_path_label = QLabel('Путь')
        java_path_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.java_path_edit = QLineEdit()
        self.java_path_edit.setPlaceholderText('Например: C:/Program Files/Java/jre/bin/java.exe')
        self.java_path_edit.setStyleSheet("""
            QLineEdit { background-color: #3d3d3d; border: 1px solid #555555; border-radius: 4px; padding: 4px 6px; color: white; font-size: 15px; }
            QLineEdit:focus { border: 1px solid #0078d7; }
        """)
        self.choose_java_btn = QPushButton('...')
        self.choose_java_btn.setFixedWidth(32)
        self.choose_java_btn.setStyleSheet('background-color: #3d3d3d; border: 1px solid #555555; border-radius: 4px; color: white;')
        self.choose_java_btn.clicked.connect(self._choose_java_path)
        self.open_java_folder_btn = QPushButton('Открыть папку')
        self.open_java_folder_btn.setStyleSheet('background-color: #3d3d3d; border: 1px solid #555555; border-radius: 4px; color: white; padding: 2px 10px;')
        self.open_java_folder_btn.clicked.connect(self._open_java_folder)
        java_path_row.addWidget(java_path_label)
        java_path_row.addWidget(self.java_path_edit)
        java_path_row.addWidget(self.choose_java_btn)
        java_path_row.addWidget(self.open_java_folder_btn)
        java_layout.addLayout(java_path_row)

        # Оптимизированные аргументы
        optimized_row = QHBoxLayout()
        optimized_label = QLabel('Оптимизированные аргументы')
        optimized_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.jre_optimized_combo = self._NoWheelCombo()
        self.jre_optimized_combo.setStyleSheet('color: #ffffff; background-color: #3d3d3d;')
        self.jre_optimized_combo.addItem('По умолчанию (G1 GC)', 'auto')
        self.jre_optimized_combo.addItem('G1 GC', 'g1gc')
        self.jre_optimized_combo.addItem('Без оптимизаций', 'none')
        optimized_row.addWidget(optimized_label)
        optimized_row.addWidget(self.jre_optimized_combo)
        java_layout.addLayout(optimized_row)

        # Java аргументы
        jre_args_layout = QVBoxLayout()
        jre_args_label = QLabel('Аргументы Java')
        jre_args_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.jre_args_edit = QLineEdit()
        self.jre_args_edit.setPlaceholderText('Например: -agentlib:, -Xms, -Dfile.encoding=UTF-8')
        self.jre_args_edit.setStyleSheet("""
            QLineEdit { background-color: #3d3d3d; border: 1px solid #555555; border-radius: 4px; padding: 4px 6px; color: white; font-size: 15px; }
            QLineEdit:focus { border: 1px solid #0078d7; }
        """)
        self.jre_args_edit.textChanged.connect(self._save_jre_args_setting)
        jre_args_layout.addWidget(jre_args_label)
        jre_args_layout.addWidget(self.jre_args_edit)
        java_layout.addLayout(jre_args_layout)

        # Обновлять устаревшие SSL-сертификаты
        self.ssl_legacy_checkbox = QCheckBox('Обновлять устаревшие SSL-сертификаты')
        self.ssl_legacy_checkbox.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.ssl_legacy_checkbox.toggled.connect(self._save_ssl_legacy_setting)
        java_layout.addWidget(self.ssl_legacy_checkbox)

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
        self.memory_slider = self._NoWheelSlider(Qt.Orientation.Horizontal)
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

        # Аргументы Minecraft
        mc_args_layout = QVBoxLayout()
        mc_args_label = QLabel('Аргументы Minecraft')
        mc_args_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.mc_args_edit = QLineEdit()
        self.mc_args_edit.setPlaceholderText('Например: --server, --port')
        self.mc_args_edit.setStyleSheet("""
            QLineEdit { background-color: #3d3d3d; border: 1px solid #555555; border-radius: 4px; padding: 4px 6px; color: white; font-size: 15px; }
            QLineEdit:focus { border: 1px solid #0078d7; }
        """)
        self.mc_args_edit.textChanged.connect(self._save_mc_args_setting)
        mc_args_layout.addWidget(mc_args_label)
        mc_args_layout.addWidget(self.mc_args_edit)
        game_layout.addLayout(mc_args_layout)

        # Команда-обёртка
        wrapper_layout = QVBoxLayout()
        wrapper_label = QLabel('Команда-обёртка (используйте %command%)')
        wrapper_label.setStyleSheet('color: #ffffff; font-size: 15px;')
        self.wrapper_edit = QLineEdit()
        self.wrapper_edit.setPlaceholderText('Например: manghoul --dslym %command%')
        self.wrapper_edit.setStyleSheet("""
            QLineEdit { background-color: #3d3d3d; border: 1px solid #555555; border-radius: 4px; padding: 4px 6px; color: white; font-size: 15px; }
            QLineEdit:focus { border: 1px solid #0078d7; }
        """)
        self.wrapper_edit.textChanged.connect(self._save_wrapper_setting)
        wrapper_layout.addWidget(wrapper_label)
        wrapper_layout.addWidget(self.wrapper_edit)
        game_layout.addLayout(wrapper_layout)

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

        # Аккаунт Ely.by (карточку создаём всегда, кнопку показываем только при входе)
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
        if self.parent_window is not None:
            self.ely_logout_button.clicked.connect(self.parent_window.ely_logout)
        ely_layout.addWidget(self.ely_logout_button)
        # Устанавливаем начальную видимость в зависимости от наличия сессии
        has_session = bool(getattr(self.parent_window, 'ely_session', None))
        self.ely_logout_button.setVisible(has_session)
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

        # Обновления лаунчера
        updates_card = QWidget()
        updates_card.setStyleSheet(card_style)
        updates_layout = QVBoxLayout(updates_card)
        updates_layout.setSpacing(7)
        updates_header = QLabel('Обновления')
        updates_header.setStyleSheet(header_style)
        updates_layout.addWidget(updates_header)

        self.check_updates_checkbox = QCheckBox('Проверять обновления при запуске')
        self.check_updates_checkbox.setStyleSheet("""
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
        updates_layout.addWidget(self.check_updates_checkbox)

        self.auto_update_checkbox = QCheckBox('Автоматически устанавливать обновления')
        self.auto_update_checkbox.setStyleSheet(self.check_updates_checkbox.styleSheet())
        updates_layout.addWidget(self.auto_update_checkbox)

        # Кнопка ручной проверки обновлений
        self.check_updates_now_btn = QPushButton('Проверить обновления сейчас')
        self.check_updates_now_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 10px;
                color: white;
                font-size: 15px;
            }
            QPushButton:hover { background-color: #4d4d4d; }
        """)
        if self.parent_window and hasattr(self.parent_window, 'check_for_updates'):
            self.check_updates_now_btn.clicked.connect(lambda: self.parent_window.check_for_updates(auto=False))
        updates_layout.addWidget(self.check_updates_now_btn)

        # Сохранение настроек обновлений
        def save_updates_settings():
            if self.parent_window:
                self.parent_window.settings['check_updates_on_start'] = self.check_updates_checkbox.isChecked()
                self.parent_window.settings['auto_update'] = self.auto_update_checkbox.isChecked()
                save_settings(self.parent_window.settings)

        self.check_updates_checkbox.toggled.connect(save_updates_settings)
        self.auto_update_checkbox.toggled.connect(save_updates_settings)

        settings_layout.addWidget(updates_card)

        # Переносим настройки Java в самый низ
        settings_layout.addWidget(java_card)

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
        
        # Java
        mode = (settings.get('java_mode') or 'recommended') if isinstance(settings, dict) else 'recommended'
        if mode == 'current':
            self.java_radio_current.setChecked(True)
        elif mode == 'custom':
            self.java_radio_custom.setChecked(True)
        else:
            self.java_radio_recommended.setChecked(True)
        self.java_path_edit.setText(settings.get('java_path', ''))
        self.jre_args_edit.setText(settings.get('jre_args', '') if isinstance(settings, dict) else '')
        self.ssl_legacy_checkbox.setChecked(bool(settings.get('update_legacy_ssl', False)))
        preset = settings.get('jre_optimized_profile', 'auto')
        idx = max(0, self.jre_optimized_combo.findData(preset if preset in ('auto','g1gc','none') else 'auto'))
        self.jre_optimized_combo.setCurrentIndex(idx)
        # Game
        self.mc_args_edit.setText(settings.get('mc_args', ''))
        self.wrapper_edit.setText(settings.get('wrapper_cmd', ''))

        # Enable/disable path controls by mode
        def update_java_controls():
            custom = self.java_radio_custom.isChecked()
            self.java_path_edit.setEnabled(custom)
            self.choose_java_btn.setEnabled(custom)
            self.open_java_folder_btn.setEnabled(custom and bool(self.java_path_edit.text()))
            # Save selection
            if self.parent_window:
                self.parent_window.settings['java_mode'] = 'custom' if self.java_radio_custom.isChecked() else ('current' if self.java_radio_current.isChecked() else 'recommended')
                save_settings(self.parent_window.settings)
        self.java_radio_recommended.toggled.connect(update_java_controls)
        self.java_radio_current.toggled.connect(update_java_controls)
        self.java_radio_custom.toggled.connect(update_java_controls)
        self.java_path_edit.textChanged.connect(self._save_java_path_setting)
        update_java_controls()

        
        if 'jre_args' in settings:
            try:
                self.jre_args_edit.setText(str(settings['jre_args'] or ''))
            except Exception:
                self.jre_args_edit.setText('')
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

        # Загружаем настройки обновлений
        if 'check_updates_on_start' in settings:
            self.check_updates_checkbox.setChecked(bool(settings['check_updates_on_start']))
        if 'auto_update' in settings:
            self.auto_update_checkbox.setChecked(bool(settings['auto_update']))

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

    

    def update_logout_button_visibility(self):
        """Обновляет видимость кнопки выхода из Ely.by"""
        # Проверяем, есть ли кнопка выхода
        if not hasattr(self, 'ely_logout_button'):
            logging.debug('ely_logout_button не найдена в SettingsTab')
            return
        
        # Проверяем наличие сессии
        has_session = bool(getattr(self.parent_window, 'ely_session', None))
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

    def _save_jre_args_setting(self):
        if self.parent_window and hasattr(self.parent_window, 'settings'):
            self.parent_window.settings['jre_args'] = self.jre_args_edit.text()
            save_settings(self.parent_window.settings)

    def _save_java_path_setting(self):
        if self.parent_window and hasattr(self.parent_window, 'settings'):
            self.parent_window.settings['java_path'] = self.java_path_edit.text()
            save_settings(self.parent_window.settings)

    def _save_ssl_legacy_setting(self, checked: bool):
        if self.parent_window and hasattr(self.parent_window, 'settings'):
            self.parent_window.settings['update_legacy_ssl'] = bool(checked)
            save_settings(self.parent_window.settings)

    def _save_mc_args_setting(self):
        if self.parent_window and hasattr(self.parent_window, 'settings'):
            self.parent_window.settings['mc_args'] = self.mc_args_edit.text()
            save_settings(self.parent_window.settings)

    def _save_wrapper_setting(self):
        if self.parent_window and hasattr(self.parent_window, 'settings'):
            self.parent_window.settings['wrapper_cmd'] = self.wrapper_edit.text()
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
            # Обновляем существующий словарь настроек, чтобы не терять неизвестные ключи
            current = dict(self.parent_window.settings or {})
            current.update({
                'close_on_launch': self.close_on_launch_checkbox.isChecked(),
                'memory': self.memory_slider.value(),
                'minecraft_directory': self.directory_edit.text(),
                'mods_directory': self.mods_directory_edit.text(),
                'java_mode': 'custom' if self.java_radio_custom.isChecked() else ('current' if self.java_radio_current.isChecked() else 'recommended'),
                'java_path': self.java_path_edit.text(),
                'jre_optimized_profile': self.jre_optimized_combo.currentData() or 'auto',
                'jre_args': self.jre_args_edit.text(),
                'update_legacy_ssl': self.ssl_legacy_checkbox.isChecked(),
                'mc_args': self.mc_args_edit.text(),
                'wrapper_cmd': self.wrapper_edit.text(),
                'show_console': self.show_console_checkbox.isChecked(),
                'hide_console_after_launch': self.hide_console_checkbox.isChecked(),
                'check_running_processes': self.check_running_processes_checkbox.isChecked(),
            })
            self.parent_window.settings = current
            save_settings(current)

    def _choose_java_path(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, 'Выберите java.exe/java', filter='Java executable (java*);;All files (*)')
            if path:
                self.java_path_edit.setText(path)
                self._save_java_path_setting()
        except Exception as e:
            logging.exception(f'Ошибка выбора Java: {e}')
            self.show_error_message('Ошибка выбора Java')

    def _open_java_folder(self):
        try:
            path = self.java_path_edit.text()
            if not path:
                return
            folder = os.path.dirname(path)
            if os.name == 'nt':
                subprocess.Popen(f'explorer "{folder}"')
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', folder])
        except Exception as e:
            logging.exception(f'Ошибка открытия папки Java: {e}')
