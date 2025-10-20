import json
import requests
from PyQt5.QtCore import QThread, pyqtSignal


class PopularModsThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, version=None, loader=None, project_type=None):
        super().__init__()
        self.version = version
        self.loader = loader
        self.project_type = project_type  # 'mod' | 'resourcepack' | 'shader' | None

    def run(self):
        try:
            # Формируем параметры запроса для популярных модов
            params = {
                'limit': 50,
                'index': 'downloads',
            }
            facets = []

            # Добавляем версию
            if self.version and self.version != 'Все версии':
                facets.append([f'versions:{self.version}'])

            # Добавляем лоадер
            if self.loader and self.loader.lower() != 'vanilla':
                facets.append([f'categories:{self.loader.lower()}'])

            # Тип проекта (моды/ресурспаки/шейдеры)
            if self.project_type in ('mod', 'resourcepack', 'shader'):
                facets.append([f'project_type:{self.project_type}'])

            # Если есть facets, преобразуем их в строку
            if facets:
                params['facets'] = json.dumps(facets)

            # Выполняем запрос
            response = requests.get('https://api.modrinth.com/v2/search', params=params)
            if response.status_code == 200:
                self.finished.emit(response.json().get('hits', []))
            else:
                self.error.emit('Не удалось загрузить популярные моды')

        except Exception as e:
            self.error.emit(str(e))
