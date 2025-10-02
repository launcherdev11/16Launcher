import json
import logging
import os
import shutil
from typing import Any
import zipfile
from functools import lru_cache

import requests

from config import MODS_DIR
from config import RESOURCEPACKS_DIR
from config import SHADERPACKS_DIR
from util import load_settings



class ModManager:
    @staticmethod
    def get_mods_directory() -> str:
        """Получает актуальный путь к папке модов из настроек"""
        settings = load_settings()
        mods_dir = settings.get('mods_directory', MODS_DIR)
        logging.debug(f'Папка модов из настроек: {mods_dir}')
        return mods_dir
    
    @staticmethod
    def get_mods_list(version: str) -> list[str]:
        """Получает список установленных модов для конкретной версии"""
        base_mods_dir = ModManager.get_mods_directory()
        version_mods_dir = os.path.join(base_mods_dir, version)
        
        mods = []
        
        # Сначала проверяем папку версии
        if os.path.exists(version_mods_dir):
            try:
                version_mods = [f for f in os.listdir(version_mods_dir) 
                              if f.endswith('.jar') or f.endswith('.zip')]
                mods.extend(version_mods)
                logging.debug(f'Найдено {len(version_mods)} модов в папке версии {version}')
            except Exception as e:
                logging.exception(f'Ошибка чтения папки версии {version_mods_dir}: {e}')
        
        # Затем проверяем базовую папку модов
        if os.path.exists(base_mods_dir):
            try:
                base_mods = [f for f in os.listdir(base_mods_dir) 
                           if f.endswith('.jar') or f.endswith('.zip')]
                # Добавляем только те моды, которых еще нет в списке
                for mod in base_mods:
                    if mod not in mods:
                        mods.append(mod)
                logging.debug(f'Найдено {len(base_mods)} модов в базовой папке')
            except Exception as e:
                logging.exception(f'Ошибка чтения базовой папки модов {base_mods_dir}: {e}')
        
        logging.debug(f'Всего модов для версии {version}: {len(mods)}')
        return mods

    @staticmethod
    def install_mod_from_file(file_path: str, version: str) -> tuple[bool, str]:
        """Устанавливает мод из файла в папку версии"""
        try:
            base_mods_dir = ModManager.get_mods_directory()
            version_mods_dir = os.path.join(base_mods_dir, version)
            os.makedirs(version_mods_dir, exist_ok=True)
            dest_path = os.path.join(version_mods_dir, os.path.basename(file_path))
            shutil.copy(file_path, dest_path)
            logging.info(f'Мод установлен: {dest_path}')
            return True, 'Мод успешно установлен!'
        except Exception as e:
            logging.exception(f'Ошибка установки мода: {e}')
            return False, f'Ошибка установки мода: {e!s}'

    @staticmethod
    def remove_mod(mod_name: str, version: str) -> tuple[bool, str]:
        """Удаляет мод из папки версии или базовой папки"""
        try:
            base_mods_dir = ModManager.get_mods_directory()
            version_mods_dir = os.path.join(base_mods_dir, version)
            
            # Сначала ищем в папке версии
            version_mod_path = os.path.join(version_mods_dir, mod_name)
            if os.path.exists(version_mod_path):
                os.remove(version_mod_path)
                logging.info(f'Мод удален из папки версии: {version_mod_path}')
                return True, 'Мод успешно удален'
            
            # Если не найден в папке версии, ищем в базовой папке
            base_mod_path = os.path.join(base_mods_dir, mod_name)
            if os.path.exists(base_mod_path):
                os.remove(base_mod_path)
                logging.info(f'Мод удален из базовой папки: {base_mod_path}')
                return True, 'Мод успешно удален'
                
            return False, 'Мод не найден'
        except Exception as e:
            logging.exception(f'Ошибка удаления мода: {e}')
            return False, f'Ошибка удаления мода: {e!s}'

    @staticmethod
    def search_modrinth(
        query: str,
        version: str | None = None,
        loader: str | None = None,
        category: str | None = None,
        sort_by: str = 'relevance',
    ) -> list[dict[str, Any]]:
        try:
            # Преобразуем параметры сортировки
            sort_mapping = {
                'По релевантности': 'relevance',
                'По загрузкам': 'downloads',
                'По дате': 'newest',
            }
            sort_by = sort_mapping.get(sort_by, 'relevance')

            facets = []

            # Фильтр по версии Minecraft
            if version and version != 'Все версии':
                facets.append(['versions:' + version])

            # Фильтр по модлоадеру
            if loader and loader.lower() != 'vanilla':
                loader = loader.lower()
                if loader == 'optifine':
                    facets.append(['categories:optimization'])
                else:
                    facets.append(['categories:' + loader])

            # Фильтр по категории
            if category and category != 'Все категории':
                facets.append(['categories:' + category.lower()])

            # Формируем параметры запроса
            params = {'query': query, 'limit': 50, 'index': sort_by}

            if facets:
                params['facets'] = json.dumps(facets)

            response = requests.get('https://api.modrinth.com/v2/search', params=params)

            if response.status_code == 200:
                return response.json().get('hits', [])
            return []
        except Exception as e:
            logging.exception(f'Ошибка поиска на Modrinth: {e}')
            return []

    @staticmethod
    def search_curseforge(query: str, version: str | None = None, loader: str | None = None) -> list[dict[str, Any]]:
        """Поиск модов на CurseForge"""
        try:
            headers = {
                'x-api-key': 'YOUR_CURSEFORGE_API_KEY',  # Нужно получить API ключ
            }
            params = {
                'gameId': 432,  # Minecraft
                'searchFilter': query,
                'pageSize': 20,
            }
            if version:
                params['gameVersion'] = version
            if loader:
                params['modLoaderType'] = loader

            response = requests.get(
                'https://api.curseforge.com/v1/mods/search',
                headers=headers,
                params=params,
            )
            if response.status_code == 200:
                return response.json()['data']
            return []
        except Exception as e:
            logging.exception(f'Ошибка поиска на CurseForge: {e}')
            return []

    @staticmethod
    def download_modrinth_mod(mod_id: str, version: str) -> tuple[bool, str]:
        """Скачивает мод с Modrinth"""
        try:
            logging.info(f'Начинаем скачивание мода {mod_id} для версии {version}')
            # Получаем информацию о файле
            response = requests.get(
                f'https://api.modrinth.com/v2/project/{mod_id}/version',
            )
            if response.status_code != 200:
                logging.error(f'Ошибка получения информации о моде {mod_id}: {response.status_code}')
                return False, 'Не удалось получить информацию о моде'

            versions = response.json()
            logging.info(f'Найдено {len(versions)} версий мода {mod_id}')
            for v in versions:
                if version in v['game_versions']:
                    file_url = v['files'][0]['url']
                    file_name = v['files'][0]['filename']
                    
                    logging.info(f'Скачиваем мод {file_name} с {file_url}')

                    # Скачиваем файл в папку версии
                    base_mods_dir = ModManager.get_mods_directory()
                    version_mods_dir = os.path.join(base_mods_dir, version)
                    os.makedirs(version_mods_dir, exist_ok=True)
                    dest_path = os.path.join(version_mods_dir, file_name)

                    response = requests.get(file_url, stream=True)
                    if response.status_code == 200:
                        with open(dest_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        logging.info(f'Мод {file_name} успешно установлен в {dest_path}')
                        return True, 'Мод успешно установлен!'
                    else:
                        logging.error(f'Ошибка скачивания файла: {response.status_code}')
            logging.warning(f'Не найдена подходящая версия мода {mod_id} для Minecraft {version}')
            return False, 'Не найдена подходящая версия мода'
        except Exception as e:
            return False, f'Ошибка загрузки мода: {e!s}'

    @staticmethod
    def download_curseforge_mod(mod_id: str, version: str) -> tuple[bool, str]:
        """Скачивает мод с CurseForge"""
        try:
            headers = {'x-api-key': 'YOUR_CURSEFORGE_API_KEY'}

            # Получаем информацию о файле
            response = requests.get(
                f'https://api.curseforge.com/v1/mods/{mod_id}/files',
                headers=headers,
            )
            if response.status_code != 200:
                return False, 'Не удалось получить информацию о моде'

            files = response.json()['data']
            for file in files:
                if version in file['gameVersions']:
                    file_url = file['downloadUrl']
                    file_name = file['fileName']

                    # Скачиваем файл
                    mods_dir = ModManager.get_mods_directory()
                    os.makedirs(os.path.join(mods_dir, version), exist_ok=True)
                    dest_path = os.path.join(mods_dir, version, file_name)

                    response = requests.get(file_url, stream=True)
                    if response.status_code == 200:
                        with open(dest_path, 'wb') as f:
                            response.raw.decode_content = True
                            shutil.copyfileobj(response.raw, f)
                        return True, 'Мод успешно установлен!'
            return False, 'Не найдена подходящая версия мода'
        except Exception as e:
            return False, f'Ошибка загрузки мода: {e!s}'

    @staticmethod
    def create_modpack(version: str, mods: list[str], output_path: str) -> tuple[bool, str]:
        """Создает сборку модов"""
        try:
            mods_dir = ModManager.get_mods_directory()
            with zipfile.ZipFile(output_path, 'w') as zipf:
                # Добавляем моды
                for mod in mods:
                    mod_path = os.path.join(mods_dir, version, mod)
                    if os.path.exists(mod_path):
                        zipf.write(mod_path, os.path.join('mods', mod))

                # Добавляем файл манифеста
                manifest = {
                    'minecraft': {'version': version, 'modLoaders': []},
                    'manifestType': 'minecraftModpack',
                    'manifestVersion': 1,
                    'name': f'Modpack {version}',
                    'version': '1.0.0',
                    'author': '16Launcher',
                    'files': [],
                }

                manifest_path = os.path.join(mods_dir, 'manifest.json')
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=4)
                zipf.write(manifest_path, 'manifest.json')
                os.remove(manifest_path)

            return True, 'Сборка успешно создана!'
        except Exception as e:
            return False, f'Ошибка создания сборки: {e!s}'

    @staticmethod
    def get_mod_categories(source: str = 'modrinth') -> list[str]:
        if source == 'modrinth':
            try:
                response = requests.get('https://api.modrinth.com/v2/tag/category')
                if response.status_code == 200:
                    return [cat['name'] for cat in response.json()]
            except Exception as e:
                logging.exception(f'Ошибка получения категорий Modrinth: {e}')
        return []

    @staticmethod
    def get_mod_details(mod_id: str, source: str = 'modrinth') -> dict[str, Any] | None:
        try:
            if source == 'modrinth':
                response = requests.get(f'https://api.modrinth.com/v2/project/{mod_id}')
                if response.status_code == 200:
                    return response.json()
            elif source == 'curseforge':
                headers = {'x-api-key': 'YOUR_CURSEFORGE_API_KEY'}
                response = requests.get(
                    f'https://api.curseforge.com/v1/mods/{mod_id}',
                    headers=headers,
                )
                if response.status_code == 200:
                    return response.json()['data']
            return None
        except Exception as e:
            logging.exception(f'Ошибка получения информации о моде: {e}')
            return None

    @staticmethod
    def get_mod_icon(mod_id: str, source: str = 'modrinth') -> str | None:
        try:
            if source == 'modrinth':
                response = requests.get(f'https://api.modrinth.com/v2/project/{mod_id}')
                if response.status_code == 200:
                    data = response.json()
                    return data.get('icon_url')
            elif source == 'curseforge':
                headers = {'x-api-key': 'YOUR_CURSEFORGE_API_KEY'}
                response = requests.get(
                    f'https://api.curseforge.com/v1/mods/{mod_id}',
                    headers=headers,
                )
                if response.status_code == 200:
                    data = response.json()['data']
                    return data.get('logo', {}).get('url')
            return None
        except Exception as e:
            logging.exception(f'Ошибка получения иконки мода: {e}')
            return None

    @staticmethod
    @lru_cache(maxsize=100)
    def cached_search(
        query: str,
        version: str | None = None,
        loader: str | None = None,
        category: str | None = None,
        sort_by: str = 'relevance',
        source: str = 'modrinth',
    ) -> list[dict[str, Any]]:
        """Кэшированный поиск модов"""
        if source == 'modrinth':
            return ModManager.search_modrinth(query, version, loader, category, sort_by)
        return ModManager.search_curseforge(query, version, loader)


    @staticmethod
    def get_textures_list(version: str) -> list[str]:
        """Возвращает список доступных ресурспаков (текстур)."""
        if not os.path.exists(RESOURCEPACKS_DIR):
            return []
        return [
            f for f in os.listdir(RESOURCEPACKS_DIR)
            if f.endswith(".zip") or os.path.isdir(os.path.join(RESOURCEPACKS_DIR, f))
        ]

    @staticmethod
    def get_shaders_list(version: str) -> list[str]:
        """Возвращает список доступных шейдеров."""
        if not os.path.exists(SHADERPACKS_DIR):
            return []
        return [
            f for f in os.listdir(SHADERPACKS_DIR)
            if f.endswith(".zip") or os.path.isdir(os.path.join(SHADERPACKS_DIR, f))
        ]