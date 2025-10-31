import logging
import os
import subprocess
from typing import Any

import requests
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QShowEvent
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config import MINECRAFT_VERSIONS
from mod_manager import ModManager
from util import resource_path

from ..threads.mod_search_thread import ModSearchThread
from ..threads.popular_mods_thread import PopularModsThread


class ModsTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.search_thread = None
        self.popular_mods_thread = None
        self.current_search_query = ""
        self.current_page = 1
        self.total_pages = 1
        self.mods_data = []
        self.minecraft_versions = []
        self.is_loaded = False
        self.setup_ui()

    def _stop_thread(self, thread_attr_name: str) -> None:
        try:
            thread = getattr(self, thread_attr_name, None)
            if thread is not None:
                try:
                    # Disconnect signals to avoid late delivery to deleted widgets
                    if hasattr(thread, "search_finished"):
                        try:
                            thread.search_finished.disconnect()
                        except Exception:
                            pass
                    if hasattr(thread, "error_occurred"):
                        try:
                            thread.error_occurred.disconnect()
                        except Exception:
                            pass
                    if hasattr(thread, "finished"):
                        try:
                            thread.finished.disconnect()
                        except Exception:
                            pass
                    if hasattr(thread, "error"):
                        try:
                            thread.error.disconnect()
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    thread.requestInterruption()
                except Exception:
                    pass
                try:
                    thread.quit()
                except Exception:
                    pass
                try:
                    thread.wait(1500)
                except Exception:
                    pass
                try:
                    setattr(self, thread_attr_name, None)
                except Exception:
                    pass
        except Exception:
            pass

    def showEvent(self, event: QShowEvent) -> None:
        """Запускаем загрузку только при первом открытии вкладки"""
        if not self.is_loaded:
            self.load_popular_mods()
            self.is_loaded = True
        super().showEvent(event)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- Верхняя панель с поиском и фильтрами ---
        top_panel = QWidget()
        top_panel.setStyleSheet("""
            QWidget {
                background-color: #333333;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        top_layout = QVBoxLayout(top_panel)

        # Поисковая строка
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск модов...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #444444;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #666666;
            }
        """)
        self.search_input.returnPressed.connect(self.search_mods)
        search_layout.addWidget(self.search_input)

        self.search_button = QPushButton()
        self.search_button.setIcon(QIcon(resource_path("assets/search.png")))
        self.search_button.setIconSize(QSize(24, 24))
        self.search_button.setFixedSize(40, 40)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.search_button.clicked.connect(self.search_mods)
        search_layout.addWidget(self.search_button)
        top_layout.addLayout(search_layout)

        # Фильтры
        filters_layout = QHBoxLayout()

        # Определяем общий стиль для ComboBox
        combo_style = """
            QComboBox {
                background-color: #444444;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """

        # Версия Minecraft
        version_layout = QVBoxLayout()
        version_layout.addWidget(QLabel("Версия Minecraft:"))

        # Используем выпадающий список для выбора версии
        self.version_select = QComboBox()
        self.version_select.setFixedWidth(200)
        self.version_select.setStyleSheet(combo_style)

        # Инициализируем список версий
        self.load_minecraft_versions()

        version_layout.addWidget(self.version_select)
        filters_layout.addLayout(version_layout)

        # Модлоадер
        loader_layout = QVBoxLayout()
        loader_layout.addWidget(QLabel("Модлоадер:"))
        self.loader_combo = QComboBox()
        self.loader_combo.setFixedWidth(200)
        self.loader_combo.addItems(["Любой", "Fabric", "Forge", "Quilt"])
        self.loader_combo.setStyleSheet(combo_style)
        # Подключаем обработчик изменения модлоадера
        self.loader_combo.currentTextChanged.connect(self.on_filters_changed)
        loader_layout.addWidget(self.loader_combo)

        # Кнопка проверки Java убрана по запросу пользователя

        filters_layout.addLayout(loader_layout)

        # Категории скрыты по просьбе пользователя

        # Сортировка
        sort_layout = QVBoxLayout()
        sort_layout.addWidget(QLabel("Сортировка:"))
        self.sort_combo = QComboBox()
        self.sort_combo.setFixedWidth(200)
        self.sort_combo.addItems(
            ["По релевантности", "По загрузкам", "По дате"],
        )
        self.sort_combo.setStyleSheet(combo_style)
        # Подключаем обработчик изменения сортировки
        self.sort_combo.currentTextChanged.connect(self.on_filters_changed)
        sort_layout.addWidget(self.sort_combo)
        filters_layout.addLayout(sort_layout)

        top_layout.addLayout(filters_layout)

        extra_controls_layout = QHBoxLayout()
        self.content_type_combo = QComboBox()
        self.content_type_combo.setFixedWidth(200)
        self.content_type_combo.addItems(["Моды", "Ресурпаки", "Шейдеры"])
        self.content_type_combo.setStyleSheet(combo_style)
        self.content_type_combo.currentTextChanged.connect(
            self.on_content_type_changed,
        )
        extra_controls_layout.addWidget(QLabel("Тип контента:"))
        extra_controls_layout.addWidget(self.content_type_combo)

        self.use_current_btn = QPushButton("Использовать текущие параметры")
        self.use_current_btn.setIcon(QIcon(resource_path("assets/copy.png")))
        self.use_current_btn.setFixedHeight(32)
        self.use_current_btn.clicked.connect(self.use_current_parameters)
        extra_controls_layout.addStretch()
        extra_controls_layout.addWidget(self.use_current_btn)
        top_layout.addLayout(extra_controls_layout)
        layout.addWidget(top_panel)

        # --- Список модов ---
        self.mods_scroll = QScrollArea()
        self.mods_scroll.setWidgetResizable(True)
        self.mods_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #333333;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
        """)

        self.mods_container = QWidget()
        self.mods_layout = QVBoxLayout(self.mods_container)
        self.mods_layout.setSpacing(15)
        self.mods_scroll.setWidget(self.mods_container)
        layout.addWidget(self.mods_scroll)

        # --- Пагинация ---
        pagination_widget = QWidget()
        pagination_widget.setStyleSheet("""
            QWidget {
                background-color: #333333;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        pagination_layout = QHBoxLayout(pagination_widget)

        self.prev_page_button = QPushButton("←")
        self.prev_page_button.setFixedSize(40, 40)
        self.prev_page_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        self.prev_page_button.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_page_button)

        self.page_label = QLabel("Страница 1 из 1")
        self.page_label.setStyleSheet("color: white;")
        pagination_layout.addWidget(self.page_label)

        self.next_page_button = QPushButton("→")
        self.next_page_button.setFixedSize(40, 40)
        self.next_page_button.setStyleSheet(self.prev_page_button.styleSheet())
        self.next_page_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_page_button)

        layout.addWidget(pagination_widget)

        # Сохраняем ссылки на основные элементы управления для скрытия во время загрузки
        self.top_panel = top_panel
        self.pagination_widget = pagination_widget

        # Создаем надпись о загрузке
        self.loading_label = QLabel("Моды загружаются, подождите...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 18px;
                font-weight: bold;
                padding: 40px;
            }
        """)
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.content_type = "Моды"
        self.loading_indicator = None

    def create_mod_card(self, mod: dict[str, Any]) -> QWidget:
        """Создает карточку мода"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #333333;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #444444;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        card.setFixedHeight(120)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)

        # Иконка
        icon_label = QLabel()
        icon_label.setFixedSize(90, 90)
        icon_label.setStyleSheet(
            "background-color: #444444; border-radius: 5px;",
        )
        icon_url = ModManager.get_mod_icon(
            mod.get("project_id", mod.get("id")),
            "modrinth",
        )
        if icon_url:
            pixmap = QPixmap()
            try:
                pixmap.loadFromData(requests.get(icon_url).content)
                icon_label.setPixmap(
                    pixmap.scaled(
                        90,
                        90,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ),
                )
            except:
                pass
        layout.addWidget(icon_label)

        # Информация
        info_layout = QVBoxLayout()

        # Название
        name_label = QLabel(mod.get("title", mod.get("name", "N/A")))
        name_label.setStyleSheet(
            "color: white; font-size: 16px; font-weight: bold;",
        )
        info_layout.addWidget(name_label)

        # Описание
        desc_label = QLabel(mod.get("description", "Нет описания"))
        desc_label.setStyleSheet("color: #aaaaaa;")
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(40)
        info_layout.addWidget(desc_label)

        # Статистика
        stats_layout = QHBoxLayout()
        downloads_label = QLabel(f'📥 {mod.get("downloads", 0)}')
        downloads_label.setStyleSheet("color: #aaaaaa;")
        stats_layout.addWidget(downloads_label)
        stats_layout.addStretch()
        info_layout.addLayout(stats_layout)

        layout.addLayout(info_layout)

        # Кнопка установки
        install_button = QPushButton("Установить")
        install_button.setFixedWidth(100)
        install_button.clicked.connect(
            lambda: self.install_modrinth_mod(mod["project_id"]),
        )
        layout.addWidget(install_button)

        return card

    def create_asset_card(self, hit: dict[str, Any]) -> QWidget:
        card = QWidget()
        card.setStyleSheet("""
            QWidget { background-color: #333333; border-radius: 10px; }
            QPushButton { background-color: #444444; color: white; border: none; border-radius: 5px; padding: 8px; }
            QPushButton:hover { background-color: #555555; }
        """)
        card.setFixedHeight(120)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)

        # Иконка
        icon_label = QLabel()
        icon_label.setFixedSize(90, 90)
        icon_label.setStyleSheet(
            "background-color: #444444; border-radius: 5px;",
        )
        icon_url = ModManager.get_mod_icon(
            hit.get("project_id", hit.get("id")),
            "modrinth",
        )
        if icon_url:
            pixmap = QPixmap()
            try:
                pixmap.loadFromData(requests.get(icon_url).content)
                icon_label.setPixmap(
                    pixmap.scaled(
                        90,
                        90,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ),
                )
            except:
                pass
        layout.addWidget(icon_label)

        # Информация
        info_layout = QVBoxLayout()
        name_label = QLabel(hit.get("title", hit.get("name", "N/A")))
        name_label.setStyleSheet(
            "color: white; font-size: 16px; font-weight: bold;",
        )
        info_layout.addWidget(name_label)
        desc_label = QLabel(hit.get("description", "Нет описания"))
        desc_label.setStyleSheet("color: #aaaaaa;")
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(40)
        info_layout.addWidget(desc_label)

        stats_layout = QHBoxLayout()
        downloads_label = QLabel(f'📥 {hit.get("downloads", 0)}')
        downloads_label.setStyleSheet("color: #aaaaaa;")
        stats_layout.addWidget(downloads_label)
        stats_layout.addStretch()
        info_layout.addLayout(stats_layout)
        layout.addLayout(info_layout)

        # Кнопка установки
        install_button = QPushButton("Установить")
        install_button.setFixedWidth(100)
        project_type = (
            "resourcepack" if self.content_type == "Ресурпаки" else "shader"
        )
        install_button.clicked.connect(
            lambda: self.install_modrinth_asset(
                hit.get("project_id", hit.get("id")),
                project_type,
            ),
        )
        layout.addWidget(install_button)

        return card

    def search_mods(self):
        """Выполняет поиск модов"""
        # Ensure previous search thread is stopped before starting a new one
        self._stop_thread("search_thread")
        if self.content_type != "Моды":
            pt = (
                "resourcepack" if self.content_type == "Ресурпаки" else "shader"
            )
            self.current_search_query = self.search_input.text().strip()
            self.current_page = 1
            self.mods_data = []
            self.update_page()
            self.show_loading_indicator()
            version = self.get_selected_version()
            loader = None
            category = None
            sort_by = self.sort_combo.currentText()
            self.search_thread = ModSearchThread(
                self.current_search_query or "",
                version,
                loader,
                category,
                sort_by,
                pt,
            )
            self.search_thread.search_finished.connect(
                lambda mods, q: self.handle_search_results(mods, q),
            )
            self.search_thread.error_occurred.connect(self.handle_search_error)
            self.search_thread.start()
            return
        query = self.search_input.text().strip()

        # Если строка поиска пуста, показываем популярные моды
        if not query:
            self.load_popular_mods()
            return

        # Сохраняем текущий запрос
        self.current_search_query = query

        # Очищаем предыдущие результаты
        self.current_page = 1
        self.mods_data = []
        self.update_page()

        # Показываем индикатор загрузки
        self.show_loading_indicator()

        # Получаем параметры поиска
        version = self.get_selected_version()
        loader = self.loader_combo.currentText()
        if loader == "Любой":
            loader = None
        category = None
        sort_by = self.sort_combo.currentText()

        # Создаем и запускаем поток поиска
        self.search_thread = ModSearchThread(
            query,
            version,
            loader,
            category,
            sort_by,
        )
        self.search_thread.search_finished.connect(
            lambda mods, q: self.handle_search_results(mods, q),
        )
        self.search_thread.error_occurred.connect(self.handle_search_error)
        self.search_thread.start()

    def load_popular_mods(self):
        """Загружает список популярных модов"""
        try:
            if self.content_type != "Моды":
                # Популярные ресурспаки/шейдеры с Modrinth
                self.show_loading_state()
                version = self.get_selected_version()
                project_type = (
                    "resourcepack"
                    if self.content_type == "Ресурпаки"
                    else "shader"
                )
                self._stop_thread("popular_mods_thread")
                self.popular_mods_thread = PopularModsThread(
                    version,
                    None,
                    project_type,
                )
                self.popular_mods_thread.finished.connect(
                    self.handle_popular_mods_loaded,
                )
                self.popular_mods_thread.error.connect(
                    self.handle_popular_mods_error,
                )
                self.popular_mods_thread.start()
                return
            # Показываем индикатор загрузки и скрываем основной интерфейс
            self.show_loading_state()

            # Получаем параметры
            version = self.get_selected_version()
            loader = self.loader_combo.currentText()
            if loader == "Любой":
                loader = None

            # Остановим предыдущий поток популярных модов, если он еще работает
            self._stop_thread("popular_mods_thread")
            # Создаем и запускаем новый поток
            self.popular_mods_thread = PopularModsThread(version, loader)
            self.popular_mods_thread.finished.connect(
                self.handle_popular_mods_loaded,
            )
            self.popular_mods_thread.error.connect(
                self.handle_popular_mods_error,
            )
            self.popular_mods_thread.start()

        except Exception as e:
            self.handle_popular_mods_error(str(e))

    def load_local_assets(self):
        # Загрузка из Modrinth для ресурспаков/шейдеров
        try:
            self.show_loading_state()
            version = self.get_selected_version()
            project_type = (
                "resourcepack" if self.content_type == "Ресурпаки" else "shader"
            )
            self._stop_thread("popular_mods_thread")
            self.popular_mods_thread = PopularModsThread(
                version,
                None,
                project_type,
            )
            self.popular_mods_thread.finished.connect(
                self.handle_popular_mods_loaded,
            )
            self.popular_mods_thread.error.connect(
                self.handle_popular_mods_error,
            )
            self.popular_mods_thread.start()
        except Exception as e:
            self.handle_popular_mods_error(str(e))

    def handle_popular_mods_loaded(self, mods):
        """Обрабатывает загруженные моды"""
        self.mods_data = mods
        self.current_page = 1
        self.show_content_state()
        self.update_page()

    def handle_popular_mods_error(self, error_message):
        """Обрабатывает ошибки загрузки"""
        self.loading_label.setText(f"Ошибка загрузки: {error_message}")
        self.loading_label.setVisible(True)
        self.mods_scroll.setVisible(False)
        self.top_panel.setVisible(True)
        self.pagination_widget.setVisible(False)
        QTimer.singleShot(5000, lambda: self.show_content_state())
        logging.error(f"Ошибка загрузки популярных модов: {error_message}")

    def handle_search_results(self, mods, query):
        """Обрабатывает результаты поиска"""
        if query != self.search_input.text().strip():
            return  # Игнорируем устаревшие результаты

        self.mods_data = mods
        self.current_page = 1
        self.hide_loading_indicator()
        self.update_page()

    def handle_search_error(self, error_message):
        """Обрабатывает ошибки поиска"""
        self.hide_loading_indicator()
        QMessageBox.critical(
            self,
            "Ошибка",
            f"Не удалось выполнить поиск: {error_message}",
        )

    def prev_page(self):
        """Переход на предыдущую страницу"""
        if self.current_page > 1:
            self.current_page -= 1
            self.update_page()

    def next_page(self):
        """Переход на следующую страницу"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_page()

    def show_loading_state(self):
        """Показывает состояние загрузки - скрывает интерфейс и показывает сообщение о загрузке"""
        try:
            subject = "Моды"
            if getattr(self, "content_type", "Моды") == "Ресурпаки":
                subject = "Ресурпаки"
            elif getattr(self, "content_type", "Моды") == "Шейдеры":
                subject = "Шейдеры"
            self.loading_label.setText(f"{subject} загружаются, подождите...")
        except Exception:
            self.loading_label.setText("Загрузка, подождите...")
        self.loading_label.setVisible(True)
        self.mods_scroll.setVisible(False)
        self.top_panel.setVisible(False)
        self.pagination_widget.setVisible(False)

    def show_content_state(self):
        """Показывает основной интерфейс после загрузки"""
        self.loading_label.setVisible(False)
        self.mods_scroll.setVisible(True)
        self.top_panel.setVisible(True)
        self.pagination_widget.setVisible(True)

    def show_loading_indicator(self):
        """Показывает индикатор загрузки для поиска"""
        self.loading_indicator = QLabel("Загрузка...")
        self.loading_indicator.setAlignment(Qt.AlignCenter)
        self.loading_indicator.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 16px;
                padding: 20px;
            }
        """)
        self.mods_layout.addWidget(self.loading_indicator)

    def hide_loading_indicator(self):
        """Скрывает индикатор загрузки для поиска"""
        if hasattr(self, "loading_indicator") and self.loading_indicator:
            self.loading_indicator.setParent(None)
            self.loading_indicator.deleteLater()
            self.loading_indicator = None

    def show_no_results_message(self):
        """Показывает сообщение об отсутствии результатов"""
        no_results_label = QLabel("Ничего не найдено")
        no_results_label.setAlignment(Qt.AlignCenter)
        no_results_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 16px;
                padding: 20px;
            }
        """)
        self.mods_layout.addWidget(no_results_label)

    def update_page(self):
        """Обновляет отображение текущей страницы с модами"""
        # Очищаем текущие карточки
        while self.mods_layout.count():
            item = self.mods_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Если нет данных, показываем сообщение
        if not self.mods_data:
            self.show_no_results_message()
            return

        # Обновляем информацию о странице
        self.total_pages = (len(self.mods_data) + 9) // 10  # Округляем вверх
        self.page_label.setText(
            f"Страница {self.current_page} из {self.total_pages}",
        )
        self.prev_page_button.setEnabled(self.current_page > 1)
        self.next_page_button.setEnabled(self.current_page < self.total_pages)

        # Добавляем карточки для текущей страницы
        start = (self.current_page - 1) * 10
        end = min(start + 10, len(self.mods_data))
        if self.content_type == "Моды":
            for mod in self.mods_data[start:end]:
                self.mods_layout.addWidget(self.create_mod_card(mod))
        else:
            for hit in self.mods_data[start:end]:
                self.mods_layout.addWidget(self.create_asset_card(hit))

        # Добавляем растягивающийся элемент
        self.mods_layout.addStretch()

    def load_minecraft_versions(self):
        """Загружает и обрабатывает список версий Minecraft"""
        self.minecraft_versions = MINECRAFT_VERSIONS

        # Заполняем ComboBox версиями
        self.version_select.clear()
        if self.minecraft_versions:
            for version in self.minecraft_versions:
                self.version_select.addItem(version)
            # Выбираем первую версию по умолчанию
            self.version_select.setCurrentIndex(0)

        # Подключаем обработчик изменения версии
        self.version_select.currentTextChanged.connect(self.on_version_changed)

    def get_selected_version(self):
        """Возвращает выбранную версию"""
        return (
            self.version_select.currentText()
            if self.version_select.currentText()
            else None
        )

    def on_version_changed(self):
        """Обработчик изменения версии Minecraft"""
        # Если есть текущий поисковый запрос, выполняем поиск заново
        if self.current_search_query:
            self.search_mods()
        else:
            # Иначе загружаем популярные моды для новой версии
            self.load_popular_mods()

    def on_filters_changed(self):
        """Обработчик изменения фильтров (модлоадер, категория, сортировка)"""
        if self.content_type != "Моды":
            self.load_local_assets()
            return
        if self.current_search_query:
            self.search_mods()
        else:
            self.load_popular_mods()

    # Категории отключены

    def install_modrinth_mod(self, mod_id):
        """Устанавливает мод с Modrinth"""
        try:
            # Получаем выбранную версию Minecraft
            version = self.get_selected_version()
            if not version:
                QMessageBox.warning(self, "Ошибка", "Выберите версию Minecraft")
                return

            # Показываем индикатор загрузки
            self.show_loading_indicator()

            # Устанавливаем мод
            success, message = ModManager.download_modrinth_mod(mod_id, version)

            # Скрываем индикатор загрузки
            self.hide_loading_indicator()

            # Показываем результат
            if success:
                self.show_success_dialog(message, version)
            else:
                QMessageBox.critical(self, "Ошибка", message)

        except Exception as e:
            self.hide_loading_indicator()
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось установить мод: {e!s}",
            )
            logging.exception(f"Ошибка установки мода: {e!s}")

    def install_modrinth_asset(self, project_id: str, project_type: str):
        try:
            version = self.get_selected_version()
            if not version:
                QMessageBox.warning(self, "Ошибка", "Выберите версию Minecraft")
                return
            self.show_loading_indicator()
            success, message = ModManager.download_modrinth_project(
                project_id,
                version,
                project_type,
            )
            self.hide_loading_indicator()
            if success:
                QMessageBox.information(self, "Успех", message)
            else:
                QMessageBox.critical(self, "Ошибка", message)
        except Exception as e:
            self.hide_loading_indicator()
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось установить: {e!s}",
            )

    def on_content_type_changed(self, value: str):
        self.content_type = value
        is_mods = value == "Моды"
        self.search_input.setEnabled(is_mods)
        self.search_button.setEnabled(is_mods)
        self.loader_combo.setEnabled(is_mods)
        self.sort_combo.setEnabled(is_mods)
        # Категории отключены
        if is_mods:
            if self.current_search_query:
                self.search_mods()
            else:
                self.load_popular_mods()
        else:
            self.load_local_assets()

    def use_current_parameters(self):
        try:
            if not self.parent_window:
                return
            vtext = self.parent_window.version_select.currentText()
            if vtext:
                idx = self.version_select.findText(vtext)
                if idx >= 0:
                    self.version_select.setCurrentIndex(idx)
            ldata = self.parent_window.loader_select.currentData()
            mapping = {
                "vanilla": "Любой",
                "forge": "Forge",
                "fabric": "Fabric",
                "quilt": "Quilt",
                "optifine": "Любой",
            }
            target = mapping.get(ldata, "Любой")
            lidx = self.loader_combo.findText(target)
            if lidx >= 0:
                self.loader_combo.setCurrentIndex(lidx)
            if self.content_type == "Моды":
                if self.current_search_query:
                    self.search_mods()
                else:
                    self.load_popular_mods()
            else:
                self.load_local_assets()
        except Exception:
            pass

    def show_success_dialog(self, message: str, version: str):
        """Показывает диалог успешной установки с кнопкой открытия папки"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Успех")
        msg.setText(message)

        # Добавляем кнопку "Открыть папку"
        open_folder_btn = msg.addButton("Открыть папку", QMessageBox.ActionRole)
        ok_btn = msg.addButton(QMessageBox.Ok)

        msg.exec_()

        # Если нажата кнопка "Открыть папку"
        if msg.clickedButton() == open_folder_btn:
            self.open_mods_folder(version)

    def open_mods_folder(self, version: str):
        """Открывает папку с модами"""
        try:
            # Пытаемся получить путь из настроек главного окна
            if self.parent_window and hasattr(self.parent_window, "settings"):
                mods_dir = self.parent_window.settings.get("mods_directory")
                if mods_dir:
                    logging.info(
                        f"Используем путь из настроек главного окна: {mods_dir}",
                    )
                else:
                    mods_dir = ModManager.get_mods_directory()
                    logging.info(f"Используем путь из ModManager: {mods_dir}")
            else:
                mods_dir = ModManager.get_mods_directory()
                logging.info(
                    f"Используем путь из ModManager (нет parent_window): {mods_dir}",
                )

            # Создаем папку если она не существует
            os.makedirs(mods_dir, exist_ok=True)

            # Открываем папку в проводнике
            if os.name == "nt":  # Windows
                # Используем os.startfile для Windows - самый надежный способ
                os.startfile(mods_dir)
            elif os.name == "posix":  # Linux/Mac
                subprocess.Popen(["xdg-open", mods_dir])

            logging.info(f"Команда открытия папки выполнена для: {mods_dir}")
        except Exception as e:
            logging.exception(f"Ошибка при открытии папки модов: {e}")
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось открыть папку: {e!s}",
            )
