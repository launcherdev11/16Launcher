import logging
import os
import shutil
import webbrowser
from base64 import b64encode

import requests
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from config import ELYBY_AUTH_URL, ELYBY_SKINS_URL, SKINS_DIR, ELYBY_SKIN_UPLOAD_URL


class ElyBySkinManager:
    @staticmethod
    def get_skin_url(username):
        """Получаем URL скина для указанного пользователя"""
        if not ELYBY_SKINS_URL:
            logging.warning('URL для скинов не настроен в config.py')
            return None
        try:
            response = requests.get(
                f'{ELYBY_SKINS_URL}{username}.png',
                allow_redirects=False,
            )
            if response.status_code == 200:
                return f'{ELYBY_SKINS_URL}{username}.png'
            return None
        except Exception as e:
            logging.exception(f'Ошибка при получении скина с Ely.by: {e}')
            return None

    @staticmethod
    def download_skin(username):
        """Скачиваем скин с Ely.by"""
        skin_url = ElyBySkinManager.get_skin_url(username)
        if not skin_url:
            return False

        try:
            response = requests.get(skin_url, stream=True)
            if response.status_code == 200:
                os.makedirs(SKINS_DIR, exist_ok=True)
                dest_path = os.path.join(SKINS_DIR, f'{username}.png')
                with open(dest_path, 'wb') as f:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, f)
                return True
        except Exception as e:
            logging.exception(f'Ошибка при загрузке скина: {e}')

        return False

    @staticmethod
    def authorize_and_get_skin(parent_window, username):
        """Авторизация через Ely.by и получение скина"""
        # Создаем диалоговое окно авторизации
        auth_dialog = QDialog(parent_window)
        auth_dialog.setWindowTitle('Авторизация через Ely.by')
        auth_dialog.setFixedSize(400, 300)

        layout = QVBoxLayout()

        info_label = QLabel('Для загрузки скина требуется авторизация через Ely.by')
        layout.addWidget(info_label)

        email_label = QLabel('Email:')
        layout.addWidget(email_label)

        email_input = QLineEdit()
        layout.addWidget(email_input)

        password_label = QLabel('Пароль:')
        layout.addWidget(password_label)

        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(password_input)

        buttons_layout = QHBoxLayout()

        login_button = QPushButton('Войти')
        buttons_layout.addWidget(login_button)

        web_auth_button = QPushButton('Войти через браузер')
        buttons_layout.addWidget(web_auth_button)

        layout.addLayout(buttons_layout)

        status_label = QLabel()
        layout.addWidget(status_label)

        auth_dialog.setLayout(layout)

        def try_login():
            email = email_input.text()
            password = password_input.text()

            if not email or not password:
                status_label.setText('Введите email и пароль')
                return

            try:
                # Формируем Basic Auth заголовок
                auth_string = f'{email}:{password}'
                auth_bytes = auth_string.encode('ascii')
                auth_b64 = b64encode(auth_bytes).decode('ascii')

                headers = {
                    'Authorization': f'Basic {auth_b64}',
                    'Content-Type': 'application/json',
                }

                # Отправляем запрос на авторизацию
                response = requests.post(
                    f'{ELYBY_AUTH_URL}/token',
                    headers=headers,
                    json={
                        'grant_type': 'password',
                        'username': email,
                        'password': password,
                    },
                )

                if response.status_code == 200:
                    # Успешная авторизация, получаем скин
                    if ElyBySkinManager.download_skin(username):
                        status_label.setText('Скин успешно загружен!')
                        QTimer.singleShot(2000, auth_dialog.accept)
                    else:
                        status_label.setText('Не удалось загрузить скин')
                else:
                    status_label.setText('Ошибка авторизации')

            except Exception as e:
                logging.exception(f'Ошибка авторизации: {e}')
                status_label.setText('Ошибка соединения')

        def open_browser_auth():
            webbrowser.open(
                'https://account.ely.by/oauth2/v1/auth?response_type=code&client_id=16launcher&redirect_uri=http://localhost&scope=skin',
            )
            status_label.setText('Пожалуйста, авторизуйтесь в браузере')

        login_button.clicked.connect(try_login)
        web_auth_button.clicked.connect(open_browser_auth)

        auth_dialog.exec_()
