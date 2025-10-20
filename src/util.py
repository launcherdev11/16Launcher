import json
import logging
import os
import random
import shutil
import sys
from typing import Any

import requests

from config import (
    AUTHLIB_INJECTOR_URL,
    AUTHLIB_JAR_PATH,
    MINECRAFT_DIR,
    SETTINGS_PATH,
    adjectives,
    default_settings,
    nouns,
    numbers,
)


def setup_directories():
    """Создает все необходимые директории при запуске"""
    try:
        os.makedirs(MINECRAFT_DIR, exist_ok=True)
    except Exception as e:
        logging.exception(f'Не удалось создать директорию: {e}')
        raise


def load_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, encoding='utf-8') as f:
                loaded_settings = json.load(f)
                return {**default_settings, **loaded_settings}
        except Exception as e:
            logging.exception(f'Ошибка загрузки настроек: {e}')
            return default_settings
    return default_settings


def save_settings(settings):
    try:
        os.makedirs(MINECRAFT_DIR, exist_ok=True)
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        logging.debug('Настройки успешно сохранены')
    except Exception as e:
        logging.exception(f'Ошибка при сохранении настроек: {e}')
    if 'export_path' not in settings:
        settings['export_path'] = os.path.expanduser('~/Desktop')


def generate_random_username():
    """Генерирует случайное имя пользователя для Minecraft"""
    # Выбираем случайные элементы
    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    num = random.choice(numbers) if random.random() > 0.5 else ''

    # Собираем имя
    if num:
        return f'{adj}{noun}{num}'
    return f'{adj}{noun}'


def download_authlib_injector():
    """Скачивает последнюю версию Authlib Injector"""
    try:
        response = requests.get(AUTHLIB_INJECTOR_URL)
        data = response.json()
        download_url = data['download_url']

        response = requests.get(download_url, stream=True)
        with open(AUTHLIB_JAR_PATH, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        return True
    except Exception as e:
        logging.exception(f'Ошибка загрузки Authlib Injector: {e}')
        return False


def download_optifine(version: str):
    try:
        url = 'https://optifine.net/downloads'
        response = requests.get(url)
        if response.status_code != 200:
            return None, 'Не удалось получить страницу загрузки OptiFine.'

        pattern = f'OptiFine {version}'
        if pattern not in response.text:
            return None, f'Версия OptiFine {version} не найдена на сайте.'

        return 'https://optifine.net/downloads', None

    except Exception as e:
        return None, f'Ошибка загрузки: {e}'


def install_optifine(version: str):
    link, error = download_optifine(version)
    if error:
        return False, error

    import webbrowser

    webbrowser.open(link)
    return True, f'Открой сайт и скачай OptiFine {version} вручную.'


def get_quilt_versions(mc_version: str) -> list[dict[str, Any]]:
    """Получает версии Quilt через minecraft-launcher-lib"""
    try:
        from minecraft_launcher_lib.quilt import get_all_loader_versions, is_minecraft_version_supported
        
        # Проверяем, поддерживается ли версия Minecraft
        if not is_minecraft_version_supported(mc_version):
            logging.warning(f'Minecraft версия {mc_version} не поддерживается Quilt')
            return []
        
        # Получаем все версии лоадера
        loader_versions = get_all_loader_versions()
        
        # Фильтруем версии для конкретной версии MC
        filtered_versions = []
        for loader in loader_versions:
            # Проверяем, что лоадер поддерживает нужную версию MC
            if hasattr(loader, 'minecraft_version') and mc_version in str(loader.get('minecraft_version', '')):
                filtered_versions.append({
                    'version': loader['version'],
                    'minecraft_version': mc_version,
                    'stable': not loader['version'].lower().startswith('beta'),
                })
        
        # Если не нашли специфичные версии, возвращаем все доступные
        if not filtered_versions:
            return [
                {
                    'version': loader['version'],
                    'minecraft_version': mc_version,
                    'stable': not loader['version'].lower().startswith('beta'),
                }
                for loader in loader_versions[:10]  # Берем первые 10 версий
            ]
        
        return filtered_versions[:10]  # Ограничиваем количество версий
        
    except ImportError:
        logging.error('minecraft-launcher-lib не установлен')
        return []
    except Exception as e:
        logging.exception(f'Quilt version fetch failed: {e!s}')
        return []


def authenticate_ely_by(username, password) -> dict[str, Any] | None:
    url = 'https://authserver.ely.by/authenticate'
    headers = {'Content-Type': 'application/json'}
    payload = {
        'agent': {'name': 'Minecraft', 'version': 1},
        'username': username,
        'password': password,
        'requestUser': True,
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return {
            'access_token': data['accessToken'],
            'client_token': data['clientToken'],
            'uuid': data['selectedProfile']['id'],
            'username': data['selectedProfile']['name'],
            'user': data.get('user', {}),
        }
    print('Ошибка авторизации:', response.text)
    return None


def resource_path(relative_path):
    """Универсальная функция для получения путей ресурсов"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    return os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')), relative_path)


def read(path):
    with open(path) as f:
        return json.load(f)


def write(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
