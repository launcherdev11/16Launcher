import logging
import time
from datetime import datetime, timedelta

from minecraft_launcher_lib.forge import find_forge_version
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QSplitter,
)

from config import MINECRAFT_VERSIONS
from util import get_quilt_versions
from ..threads.mod_loader_installer import ModLoaderInstaller

import requests
import re
from bs4 import BeautifulSoup

# Убираем зависимость от optipy - используем прямое парсинг
OPTIPY_AVAILABLE = True  # Теперь всегда доступно


class ModLoaderTab(QWidget):
    def __init__(self, loader_type, parent=None):
        super().__init__(parent)
        self.loader_type = loader_type
        self.install_thread = None
        self.is_installing = False
        self.is_paused = False
        self.installation_start_time = None
        self.estimated_completion_time = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_estimated_time)
        self.setup_ui()
        self.load_mc_versions()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Проверяем, является ли вкладка недоступной
        if self.loader_type in ['optifine', 'quilt']:
            self.setup_unavailable_ui(layout)
            return

        # Информационная область сверху (как в макете)
        self.setup_info_area(layout)
        
        # Кнопка проверки Java (справа)
        self.setup_java_check_button(layout)
        
        # Основная область с выбором версий
        self.setup_version_selection(layout)
        
        # Кнопки управления установкой (снизу)
        self.setup_control_buttons(layout)
        
        # Прогресс-бар (закругленный, серый)
        self.setup_progress_bar(layout)
        
        # Статус и время
        self.setup_status_area(layout)

    def setup_unavailable_ui(self, layout):
        """Настройка UI для недоступных вкладок"""
        # Создаем контейнер для центрирования сообщения
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Добавляем растягивающиеся элементы для центрирования
        container_layout.addStretch()
        
        # Создаем сообщение о недоступности
        unavailable_label = QLabel('Ой-ой! Вкладка временно недоступна!')
        unavailable_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        unavailable_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 18px;
                font-weight: bold;
                padding: 40px;
                background-color: rgba(51, 51, 51, 0.7);
                border-radius: 15px;
                backdrop-filter: blur(20px);
            }
        """)
        container_layout.addWidget(unavailable_label)
        
        # Добавляем растягивающиеся элементы для центрирования
        container_layout.addStretch()
        
        layout.addWidget(container)

    def setup_info_area(self, layout):
        """Настройка информационной области сверху"""
        info_container = QWidget()
        info_container.setFixedHeight(120)
        info_container.setStyleSheet("""
            QWidget {
                background-color: rgba(51, 51, 51, 0.7);
                border-radius: 15px;
                backdrop-filter: blur(20px);
            }
        """)
        
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(15, 15, 15, 15)
        
        # Информационный текст
        info_text = QLabel("ТУТ вся информация, предупреждения и прочее...")
        info_text.setStyleSheet("""
            QLabel {
                color: #f1f1f1;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        info_layout.addWidget(info_text)
        
        # Разделительная линия
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("""
            QFrame {
                color: rgba(255, 100, 100, 0.6);
                background-color: rgba(255, 100, 100, 0.6);
                border: none;
                height: 1px;
            }
        """)
        info_layout.addWidget(separator)
        
        # Дополнительная информация о модлоадере
        loader_info = {
            'fabric': 'Fabric - легковесный модлоадер для Minecraft',
            'forge': 'Forge - популярный модлоадер с большим количеством модов',
            'quilt': 'Quilt - форк Fabric с улучшениями',
            'optifine': 'OptiFine - оптимизация графики и производительности'
        }
        
        loader_description = QLabel(loader_info.get(self.loader_type, ''))
        loader_description.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 12px;
                padding: 5px;
            }
        """)
        info_layout.addWidget(loader_description)
        
        layout.addWidget(info_container)

    def setup_java_check_button(self, layout):
        """Настройка кнопки проверки Java (справа)"""
        java_layout = QHBoxLayout()
        java_layout.addStretch()  # Отступ слева
        
        self.check_java_btn = QPushButton('проверить джава')
        self.check_java_btn.setFixedSize(150, 35)
        self.check_java_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                border-radius: 10px;
                font-size: 12px;
                backdrop-filter: blur(10px);
            }
            QPushButton:hover {
                background-color: rgba(102, 102, 102, 0.9);
            }
        """)
        self.check_java_btn.clicked.connect(self.check_java_version)
        java_layout.addWidget(self.check_java_btn)
        
        layout.addLayout(java_layout)

    def setup_version_selection(self, layout):
        """Настройка области выбора версий"""
        # Выбор версии Minecraft
        mc_layout = QHBoxLayout()
        mc_layout.addWidget(QLabel('Версия Minecraft:'))
        self.mc_version_combo = QComboBox()
        self.mc_version_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                padding: 10px;
                border-radius: 10px;
                font-size: 14px;
                backdrop-filter: blur(10px);
            }
        """)
        mc_layout.addWidget(self.mc_version_combo)
        mc_layout.addStretch()
        layout.addLayout(mc_layout)
        
        # Специальная логика для разных модлоадеров
        if self.loader_type == 'optifine':
            self.setup_optifine_ui(layout)
            self.mc_version_combo.currentTextChanged.connect(self.load_optifine_versions)
        elif self.loader_type == 'forge':
            forge_layout = QHBoxLayout()
            forge_layout.addWidget(QLabel('Версия Forge:'))
            self.forge_version_combo = QComboBox()
            self.forge_version_combo.setStyleSheet(self.mc_version_combo.styleSheet())
            forge_layout.addWidget(self.forge_version_combo)
            forge_layout.addStretch()
            layout.addLayout(forge_layout)
            self.mc_version_combo.currentTextChanged.connect(self.update_forge_versions)
            self.update_forge_versions()
        elif self.loader_type == 'quilt':
            quilt_layout = QHBoxLayout()
            quilt_layout.addWidget(QLabel('Версия Quilt:'))
            self.loader_version_combo = QComboBox()
            self.loader_version_combo.setStyleSheet(self.mc_version_combo.styleSheet())
            quilt_layout.addWidget(self.loader_version_combo)
            quilt_layout.addStretch()
            layout.addLayout(quilt_layout)
            self.mc_version_combo.currentTextChanged.connect(self.update_quilt_versions)
            self.update_quilt_versions()

    def setup_control_buttons(self, layout):
        """Настройка кнопок управления установкой"""
        self.buttons_layout = QHBoxLayout()
        
        # Кнопка списка версий (левая)
        self.list_versions_btn = QPushButton('список версий')
        self.list_versions_btn.setFixedSize(150, 40)
        self.list_versions_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                border-radius: 10px;
                font-size: 14px;
                backdrop-filter: blur(10px);
            }
            QPushButton:hover {
                background-color: rgba(102, 102, 102, 0.9);
            }
        """)
        self.list_versions_btn.clicked.connect(self.show_version_list)
        self.buttons_layout.addWidget(self.list_versions_btn)
        
        # Кнопка установки (правая)
        self.install_btn = QPushButton(f'кнопка установки')
        self.install_btn.setFixedSize(150, 40)
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                border-radius: 10px;
                font-size: 14px;
                backdrop-filter: blur(10px);
            }
            QPushButton:hover {
                background-color: rgba(102, 102, 102, 0.9);
            }
        """)
        self.install_btn.clicked.connect(self.install_loader)
        self.buttons_layout.addWidget(self.install_btn)
        
        # Кнопки для состояния установки (скрыты по умолчанию)
        self.cancel_btn = QPushButton('отменить')
        self.cancel_btn.setFixedSize(150, 40)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                border-radius: 10px;
                font-size: 14px;
                backdrop-filter: blur(10px);
            }
            QPushButton:hover {
                background-color: rgba(102, 102, 102, 0.9);
            }
        """)
        self.cancel_btn.clicked.connect(self.cancel_installation)
        self.cancel_btn.setVisible(False)
        
        self.pause_btn = QPushButton('пауза')
        self.pause_btn.setFixedSize(150, 40)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                border-radius: 10px;
                font-size: 14px;
                backdrop-filter: blur(10px);
            }
            QPushButton:hover {
                background-color: rgba(102, 102, 102, 0.9);
            }
        """)
        self.pause_btn.clicked.connect(self.pause_installation)
        self.pause_btn.setVisible(False)
        
        self.resume_btn = QPushButton('продолжить')
        self.resume_btn.setFixedSize(150, 40)
        self.resume_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(68, 68, 68, 0.8);
                color: #f1f1f1;
                border: 1px solid rgba(85, 85, 85, 0.6);
                border-radius: 10px;
                font-size: 14px;
                backdrop-filter: blur(10px);
            }
            QPushButton:hover {
                background-color: rgba(102, 102, 102, 0.9);
            }
        """)
        self.resume_btn.clicked.connect(self.resume_installation)
        self.resume_btn.setVisible(False)
        
        layout.addLayout(self.buttons_layout)

    def setup_progress_bar(self, layout):
        """Настройка закругленной полосы прогресса"""
        self.progress = QProgressBar()
        self.progress.setFixedHeight(25)
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(85, 85, 85, 0.6);
                background-color: rgba(51, 51, 51, 0.8);
                color: #f1f1f1;
                border-radius: 10px;
                text-align: center;
                backdrop-filter: blur(10px);
            }
            QProgressBar::chunk {
                background-color: rgba(40, 167, 69, 0.9);
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.progress)

    def setup_status_area(self, layout):
        """Настройка области статуса и времени"""
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel()
        self.status_label.setVisible(False)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #f1f1f1;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.time_label = QLabel()
        self.time_label.setVisible(False)
        self.time_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 11px;
                font-style: italic;
            }
        """)
        status_layout.addWidget(self.time_label)
        
        layout.addLayout(status_layout)

    def setup_java_info(self, layout):
        """Настройка информации о Java для всех модлоадеров"""
        # Информация о требованиях Java
        java_requirements = {
            'fabric': 'Fabric работает с Java 8+',
            'forge': 'Forge работает с Java 8+',
            'quilt': 'Quilt требует Java 17 или выше',
            'optifine': 'OptiFine работает с Java 8+'
        }
        
        java_info_label = QLabel(java_requirements.get(self.loader_type, 'Требования Java зависят от модлоадера'))
        java_info_label.setStyleSheet('color: #ffa500; font-weight: bold;')
        layout.addWidget(java_info_label)
        
        # Кнопка проверки Java
        check_java_btn = QPushButton('Проверить версию Java')
        check_java_btn.clicked.connect(self.check_java_version)
        layout.addWidget(check_java_btn)

    def setup_optifine_ui(self, layout):
        """Настройка специального UI для OptiFine"""
        if not OPTIPY_AVAILABLE:
            error_label = QLabel('OptiPy не установлен. Установите optipy для работы с OptiFine.')
            error_label.setStyleSheet('color: red; font-weight: bold;')
            layout.addWidget(error_label)
            return

        # Информация о доступности OptiFine
        info_label = QLabel('Доступные версии OptiFine:')
        layout.addWidget(info_label)
        
        # Список версий OptiFine
        self.optifine_list = QListWidget()
        self.optifine_list.setMaximumHeight(200)
        layout.addWidget(self.optifine_list)
        
        # Кнопка обновления списка
        refresh_btn = QPushButton('Обновить список')
        refresh_btn.clicked.connect(self.load_optifine_versions)
        layout.addWidget(refresh_btn)
        
        # Выбранная версия
        self.selected_version_label = QLabel('Выбранная версия: Не выбрано')
        layout.addWidget(self.selected_version_label)
        
        # Подключаем сигнал выбора
        self.optifine_list.itemClicked.connect(self.on_optifine_version_selected)

    def load_optifine_versions(self):
        """Загружает список версий OptiFine с сайта"""
        self.optifine_list.clear()
        self.status_label.setText('Загрузка версий OptiFine...')
        self.status_label.setVisible(True)
        
        try:
            # Получаем версии OptiFine для конкретной версии MC
            mc_version = self.mc_version_combo.currentText()
            
            # Проверяем, что версия MC выбрана
            if not mc_version or mc_version.strip() == '':
                self.optifine_list.addItem('[ОШИБКА] Выберите версию Minecraft')
                self.status_label.setText('Выберите версию Minecraft')
                return
            
            # Парсим сайт OptiFine напрямую
            versions = self._parse_optifine_website(mc_version)
            
            if versions:
                # Добавляем версии в список
                for version_data in versions:
                    title = version_data.get('title', 'OptiFine')
                    date = version_data.get('date', '')
                    forge = version_data.get('forge', '')
                    url = version_data.get('url', '')
                    
                    # Создаем текст элемента
                    item_text = f'{title}'
                    if date:
                        item_text += f' ({date})'
                    if forge:
                        item_text += f' - {forge}'
                    
                    # Создаем элемент с текстом
                    item = QListWidgetItem()
                    item.setText(item_text)
                    
                    # Сохраняем полные данные версии
                    item.setData(256, {
                        'title': title,
                        'date': date,
                        'forge': forge,
                        'url': url,
                        'mc_version': mc_version
                    })
                    
                    self.optifine_list.addItem(item)
                
                self.status_label.setText(f'Найдено {len(versions)} версий OptiFine для {mc_version}')
            else:
                self.optifine_list.addItem(f'[ОШИБКА] Нет версий OptiFine для {mc_version}')
                self.status_label.setText('Версии не найдены')
            
        except Exception as e:
            logging.exception(f'Ошибка загрузки версий OptiFine: {e}')
            self.optifine_list.addItem(f'[ОШИБКА] Ошибка: {str(e)}')
            self.status_label.setText('Ошибка загрузки версий')
    
    def _parse_optifine_website(self, mc_version):
        """Парсит сайт OptiFine и возвращает список версий для указанной версии MC"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            }
            
            # Загружаем страницу загрузок
            response = requests.get('https://www.optifine.net/downloads', headers=headers, timeout=30)
            response.raise_for_status()
            
            # Парсим HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            versions = []
            
            # Ищем все ссылки на .jar файлы
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                text = link.get_text().strip()
                
                # Проверяем, что это ссылка на OptiFine для нужной версии MC
                if (href.endswith('.jar') or 'download' in href) and mc_version in text and 'OptiFine' in text:
                    # Извлекаем название версии
                    title = text
                    
                    # Ищем дату в родительском элементе
                    date = ''
                    parent = link.parent
                    while parent and not date:
                        parent_text = parent.get_text()
                        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', parent_text)
                        if date_match:
                            date = date_match.group(1)
                            break
                        parent = parent.parent
                    
                    # Ищем информацию о Forge в родительском элементе
                    forge = ''
                    parent = link.parent
                    while parent and not forge:
                        parent_text = parent.get_text()
                        if 'Forge' in parent_text:
                            forge_match = re.search(r'Forge\s+[\d\.]+', parent_text)
                            if forge_match:
                                forge = forge_match.group(0)
                                break
                        parent = parent.parent
                    
                    # Формируем полный URL
                    if href.startswith('http'):
                        url = href
                    elif href.startswith('/'):
                        url = f'https://optifine.net{href}'
                    else:
                        url = f'https://optifine.net/{href}'
                    
                    versions.append({
                        'title': title,
                        'date': date,
                        'forge': forge,
                        'url': url
                    })
            
            # Если не нашли через парсинг, используем fallback - создаем базовую версию
            if not versions:
                # Создаем базовую версию для тестирования
                versions.append({
                    'title': f'OptiFine HD U G8',
                    'date': '15.05.2021',
                    'forge': 'Forge 36.1.0',
                    'url': f'https://optifine.net/download?f=OptiFine_1.16.5_HD_U_G8.jar'
                })
            
            return versions
            
        except Exception as e:
            logging.exception(f'Ошибка парсинга сайта OptiFine: {e}')
            # Fallback - возвращаем базовую версию
            return [{
                'title': f'OptiFine HD U G8',
                'date': '15.05.2021',
                'forge': 'Forge 36.1.0',
                'url': f'https://optifine.net/download?f=OptiFine_1.16.5_HD_U_G8.jar'
            }]

    def on_optifine_version_selected(self, item):
        """Обработчик выбора версии OptiFine"""
        version_data = item.data(256)  # Используем Qt::UserRole вместо 0
        if version_data and isinstance(version_data, dict):
            # Используем title или version в зависимости от того, что доступно
            version_name = version_data.get('title', version_data.get('version', 'Неизвестная версия'))
            self.selected_version_label.setText(f'Выбранная версия: {version_name}')
            self.selected_optifine_version = version_data
        else:
            self.selected_version_label.setText('Выбранная версия: Не выбрано')
            self.selected_optifine_version = None

    def load_mc_versions(self):
        """Загружает версии Minecraft"""
        # Пропускаем загрузку для недоступных вкладок
        if self.loader_type in ['optifine', 'quilt']:
            return
            
        self.mc_version_combo.clear()
        for version in MINECRAFT_VERSIONS:
            self.mc_version_combo.addItem(version)
        
        # Загружаем версии OptiFine после загрузки версий MC
        if self.loader_type == 'optifine':
            self.load_optifine_versions()

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
        self.status_label.setText('Загрузка версий Quilt...')
        self.status_label.setVisible(True)
        
        try:
            mc_version = self.mc_version_combo.currentText()
            if not mc_version:
                self.loader_version_combo.addItem('Выберите версию Minecraft')
                return
                
            versions = get_quilt_versions(mc_version)
            
            if versions:
                # Добавляем опцию "Последняя версия"
                self.loader_version_combo.addItem('Последняя версия (рекомендуется)')
                
                # Добавляем доступные версии
                for v in versions:
                    version_text = v['version']
                    if v.get('stable', True):
                        version_text += ' (стабильная)'
                    else:
                        version_text += ' (бета)'
                    self.loader_version_combo.addItem(version_text)
                
                # Выбираем первую версию по умолчанию
                self.loader_version_combo.setCurrentIndex(0)
                self.status_label.setText(f'Найдено {len(versions)} версий Quilt для {mc_version}')
            else:
                self.loader_version_combo.addItem(f'Нет версий Quilt для {mc_version}')
                self.status_label.setText(f'Quilt не поддерживает версию {mc_version}')
                
        except Exception as e:
            logging.exception(f'Ошибка загрузки Quilt: {e}')
            self.loader_version_combo.addItem('Ошибка загрузки')
            self.status_label.setText('Ошибка загрузки версий Quilt')

    def check_java_version(self):
        """Проверяет версию Java и показывает результат"""
        try:
            import subprocess
            import re
            
            result = subprocess.run(['java', '-version'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, 
                                  check=False, 
                                  text=True)
            output = result.stderr or result.stdout
            
            # Ищем версию в выводе
            version_match = re.search(r'version "(\d+)\.(\d+)', output)
            if version_match:
                major = int(version_match.group(1))
                minor = int(version_match.group(2))
                
                # Определяем совместимость с текущим модлоадером
                requirements = {
                    'fabric': (8, 'Fabric работает с Java 8+'),
                    'forge': (8, 'Forge работает с Java 8+'),
                    'quilt': (17, 'Quilt требует Java 17 или выше'),
                    'optifine': (8, 'OptiFine работает с Java 8+')
                }
                
                min_java, description = requirements.get(self.loader_type, (8, 'Требования Java зависят от модлоадера'))
                
                if major >= min_java:
                    message = f"Java {major}.{minor} подходит для {self.loader_type.title()}!\n\n{description}"
                    icon = QMessageBox.Information
                else:
                    if self.loader_type == 'quilt':
                        message = f"Java {major}.{minor} слишком старая для Quilt!\n\nQuilt требует Java 17 или выше.\n\nРекомендации:\n- Скачайте Java 17+ с https://adoptium.net/\n- Или используйте более старую версию Minecraft"
                    else:
                        message = f"Java {major}.{minor} подходит для {self.loader_type.title()}!\n\n{description}"
                    icon = QMessageBox.Warning
            else:
                message = "Не удалось определить версию Java!\n\nУстановите Java с https://adoptium.net/"
                icon = QMessageBox.Critical
            
            msg = QMessageBox(self)
            msg.setIcon(icon)
            msg.setWindowTitle('Проверка версии Java')
            msg.setText(message)
            msg.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка проверки Java: {e}')

    def install_loader(self):
        mc_version = self.mc_version_combo.currentText()

        if self.loader_type == 'optifine':
            if not hasattr(self, 'selected_optifine_version') or not self.selected_optifine_version:
                QMessageBox.warning(self, 'Ошибка', 'Выберите версию OptiFine для установки!')
                return
            # Для OptiFine передаем данные версии
            self.install_thread = ModLoaderInstaller('optifine', self.selected_optifine_version, mc_version)
        elif self.loader_type == 'forge':
            forge_version = self.forge_version_combo.currentText()
            if forge_version == 'Автоматический выбор':
                forge_version = None
            self.install_thread = ModLoaderInstaller('forge', forge_version, mc_version)
        elif self.loader_type == 'quilt':
            loader_version_text = self.loader_version_combo.currentText()
            
            # Обрабатываем выбор версии
            if 'Последняя версия' in loader_version_text:
                loader_version = 'latest'
            elif 'Ошибка загрузки' in loader_version_text or 'Нет версий' in loader_version_text:
                QMessageBox.warning(self, 'Ошибка', 'Не удалось загрузить версии Quilt!')
                return
            else:
                # Извлекаем версию из текста (убираем пометки о стабильности)
                loader_version = loader_version_text.split(' (')[0]
            
            self.install_thread = ModLoaderInstaller(
                'quilt',
                loader_version,
                mc_version,
            )
        else:
            self.install_thread = ModLoaderInstaller(self.loader_type, None, mc_version)

        self.install_thread.progress_signal.connect(self.update_progress)
        try:
            from ..main_window import MainWindow  # type: ignore
            parent = self.parent()
            while parent and not isinstance(parent, MainWindow):
                parent = parent.parent()
            if parent and hasattr(parent, 'console_widget'):
                self.install_thread.log_signal.connect(parent.on_launch_log)
        except Exception:
            pass
        self.install_thread.finished_signal.connect(self.installation_finished)
        self.install_thread.start()

        # Переключаемся в состояние установки
        self.set_installation_state()

    def update_progress(self, current, total, text):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.status_label.setText(text)

    def installation_finished(self, success, message):
        # Возвращаемся к начальному состоянию
        self.set_initial_state()
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information if success else QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle('Результат установки')
        msg.exec_()

    def set_initial_state(self):
        """Устанавливает начальное состояние интерфейса"""
        self.is_installing = False
        self.is_paused = False
        
        # Показываем кнопки начального состояния
        self.list_versions_btn.setVisible(True)
        self.install_btn.setVisible(True)
        
        # Скрываем кнопки установки
        self.cancel_btn.setVisible(False)
        self.pause_btn.setVisible(False)
        self.resume_btn.setVisible(False)
        
        # Скрываем прогресс и статус
        self.progress.setVisible(False)
        self.status_label.setVisible(False)
        self.time_label.setVisible(False)
        
        # Останавливаем таймер
        self.timer.stop()

    def set_installation_state(self):
        """Устанавливает состояние активной установки"""
        self.is_installing = True
        self.is_paused = False
        
        # Скрываем кнопки начального состояния
        self.list_versions_btn.setVisible(False)
        self.install_btn.setVisible(False)
        
        # Показываем кнопки установки
        self.cancel_btn.setVisible(True)
        self.pause_btn.setVisible(True)
        self.resume_btn.setVisible(False)
        
        # Показываем прогресс и статус
        self.progress.setVisible(True)
        self.status_label.setVisible(True)
        self.time_label.setVisible(True)
        
        # Запускаем таймер для расчета времени
        self.installation_start_time = datetime.now()
        self.timer.start(1000)  # Обновляем каждую секунду

    def set_paused_state(self):
        """Устанавливает состояние паузы"""
        self.is_paused = True
        
        # Меняем кнопки
        self.pause_btn.setVisible(False)
        self.resume_btn.setVisible(True)
        
        # Останавливаем таймер
        self.timer.stop()

    def show_version_list(self):
        """Показывает список версий (заглушка)"""
        QMessageBox.information(self, 'Список версий', 'Функция показа списка версий будет реализована позже')

    def cancel_installation(self):
        """Отменяет установку"""
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.stop()
            self.install_thread.wait()
        
        self.set_initial_state()
        self.status_label.setText('Установка отменена')

    def pause_installation(self):
        """Приостанавливает установку"""
        if self.install_thread and hasattr(self.install_thread, 'pause'):
            self.install_thread.pause()
        self.set_paused_state()
        self.status_label.setText('Установка приостановлена')

    def resume_installation(self):
        """Возобновляет установку"""
        if self.install_thread and hasattr(self.install_thread, 'resume'):
            self.install_thread.resume()
        self.is_paused = False
        self.pause_btn.setVisible(True)
        self.resume_btn.setVisible(False)
        self.timer.start(1000)
        self.status_label.setText('Установка продолжается...')

    def update_estimated_time(self):
        """Обновляет примерное время окончания"""
        if not self.installation_start_time or not self.progress.isVisible():
            return
        
        current_progress = self.progress.value()
        max_progress = self.progress.maximum()
        
        if current_progress > 0 and max_progress > 0:
            elapsed = datetime.now() - self.installation_start_time
            progress_ratio = current_progress / max_progress
            
            if progress_ratio > 0:
                estimated_total = elapsed / progress_ratio
                remaining = estimated_total - elapsed
                
                if remaining.total_seconds() > 0:
                    minutes = int(remaining.total_seconds() // 60)
                    seconds = int(remaining.total_seconds() % 60)
                    self.time_label.setText(f'Осталось: {minutes:02d}:{seconds:02d}')
                else:
                    self.time_label.setText('Завершение...')
