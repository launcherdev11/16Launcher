from dataclasses import dataclass
from typing import ClassVar


@dataclass
class Translator:
    language: str = "ru"
    translations: ClassVar[dict[str, dict[str, str]]] = {
        "ru": {
            "window_title": "16Launcher 1.0.3",
            "play_button": "Играть",
            "settings_button": "Настройки",
            "support_button": "Поддержать",
            "username_placeholder": "Введите имя",
            "version_label": "Версия Minecraft:",
            "loader_label": "Модлоадер:",
            "launch_button": "Играть",
            "change_skin_button": "Сменить скин",
            "ely_login_button": "Войти с Ely.by",
            "language_label": "Язык:",
            "theme_button": "Тёмная тема",
            "memory_label": "Оперативная память (ГБ):",
            "directory_label": "Директория игры:",
            "choose_directory_button": "Выбрать папку",
            "close_on_launch": "Закрывать лаунчер при запуске игры",
            "ely_logout_button": "Выйти из Ely.by",
            "enter_username": "Введите имя игрока!",
            "launch_error": "Ошибка запуска",
        },
        "en": {
            "window_title": "16Launcher 1.0.3",
            "play_button": "Play",
            "settings_button": "Settings",
            "support_button": "Support",
            "username_placeholder": "Enter username",
            "version_label": "Minecraft version:",
            "loader_label": "Mod loader:",
            "launch_button": "Play",
            "change_skin_button": "Change skin",
            "ely_login_button": "Login with Ely.by",
            "language_label": "Language:",
            "theme_button": "Dark theme",
            "memory_label": "RAM (GB):",
            "directory_label": "Game directory:",
            "choose_directory_button": "Choose folder",
            "close_on_launch": "Close launcher on game start",
            "ely_logout_button": "Logout from Ely.by",
            "enter_username": "Please enter username!",
            "launch_error": "Launch error",
        },
    }

    def set_language(self, lang: str) -> None:
        self.language = lang

    def tr(self, key: str) -> str:
        return self.translations.get(self.language, {}).get(key, key)
