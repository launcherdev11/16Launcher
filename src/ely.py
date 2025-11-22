import logging
import os

import requests

from ely_device import authorize_via_device_code
from flow import logged
from util import read, write
from config import ELYBY_SKINS_URL, ELYBY_SKIN_UPLOAD_URL, MINECRAFT_DIR, ELYBY_API_URL

LOGIN_FILE = os.path.join(MINECRAFT_DIR, 'login_data.json')


class AuthError(Exception):
    pass


@logged
def auth(login, password):
    data = _auth(login, password)
    return {
        'username': data['selectedProfile']['name'],
        'uuid': data['selectedProfile']['id'],
        'token': data['accessToken'],
    }


@logged
def _auth(login, password):
    data = {
        'username': login,
        'password': password,
        'clientToken': 'tlauncher',
        'requestUser': True,
    }
    r = requests.post(BASE_URL + '/auth/authenticate', data=data)
    if r.status_code != 200:
        raise AuthError(r.text)
    return r.json()


@logged
def username(val=None):
    if val is None:
        return read(LOGIN_FILE)['username']
    dat = read(LOGIN_FILE)
    dat['username'] = val
    write(LOGIN_FILE, dat)
    return None


@logged
def uuid(val=None):
    if val is None:
        return read(LOGIN_FILE)['uuid']
    dat = read(LOGIN_FILE)
    dat['uuid'] = val
    write(LOGIN_FILE, dat)
    return None


@logged
def token(val=None):
    if val is None:
        return read(LOGIN_FILE)['token']
    dat = read(LOGIN_FILE)
    dat['token'] = val
    write(LOGIN_FILE, dat)
    return None


@logged
def logged_in(val=None):
    if val is None:
        return read(LOGIN_FILE)['logged_in']
    dat = read(LOGIN_FILE)
    dat['logged_in'] = val
    write(LOGIN_FILE, dat)
    return None


def auth_device_code():
    """Аутентификация через device code"""
    try:
        token_data = authorize_via_device_code()
        profile = {
            'username': token_data['username'],
            'uuid': token_data.get('uuid', ''),
            'token': token_data['access_token'],
            'logged_in': True,
        }
        # Сохраняем данные входа
        write_login_data(profile)
        return profile
    except Exception as e:
        raise AuthError(f'Device code auth failed: {e!s}')


def write_login_data(data):
    """Сохраняет данные авторизации"""
    login_data = {
        'username': data['username'],
        'uuid': data.get('uuid', ''),
        'token': data['token'],
        'logged_in': data.get('logged_in', False),
    }
    write(LOGIN_FILE, login_data)


def is_logged_in():
    """Проверяет, есть ли активная сессия"""
    try:
        data = read(LOGIN_FILE)
        return data.get('logged_in', False)
    except Exception:
        return False


def logout():
    """Выход из системы"""
    write_login_data({'username': '', 'uuid': '', 'token': '', 'logged_in': False})


def auth_password(email, password):
    """Аутентификация через логин/пароль"""
    payload = {
        'username': email,
        'password': password,
        'requestUser': True,
    }

    auth_resp = requests.post(f'{ELYBY_API_URL}/authenticate', json=payload)
    if auth_resp.status_code != 200:
        raise AuthError(auth_resp.text)

    # parse authentication response and extract token (support common key names)
    auth_json = auth_resp.json()
    token = auth_json.get('access_token') or auth_json.get('accessToken') or auth_json.get('token')
    if not token:
        raise AuthError('Authentication succeeded but no access token was returned')
    


    data = auth_resp.json()
    # try to extract username and uuid from common locations
    selected = data.get('selectedProfile') or {}
    username = selected.get('name') or data.get('username') or data.get('name') or ''
    uuid = selected.get('id') or data.get('uuid') or ''

    return {
        'username': username,
        'uuid': uuid,
        'token': token,
    }


def get_skin_url(username):
    """Получает URL скина пользователя"""
    if not ELYBY_SKINS_URL:
        return None
    response = requests.get(f'{ELYBY_SKINS_URL}{username}.png')
    return response.url if response.status_code == 200 else None


def upload_skin(file_path, token, variant='classic'):
    """
    Загружает скин на Ely.by через официальный API.
    :param file_path: путь к PNG-файлу
    :param token: Bearer-токен Ely.by
    :param variant: 'classic' или 'slim'
    """
    url = 'https://account.ely.by/api/resources/skin'
    headers = {'Authorization': f'Bearer {token}'}

    with open(file_path, 'rb') as f:
        files = {'file': ('skin.png', f, 'image/png'), 'variant': (None, variant)}

        response = requests.put(url, headers=headers, files=files)

    if response.status_code == 200:
        return True
    logging.error('Ошибка загрузки скина:', response.status_code, response.text)
    return False

"""
"""