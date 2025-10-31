# config.py
import os

from minecraft_launcher_lib.utils import (
    get_minecraft_directory,
    get_version_list,
)

MINECRAFT_VERSIONS: list[str] = [
    version["id"]
    for version in get_version_list()
    if version["type"] == "release"
]
ELY_CLIENT_ID = "16Launcher"
RELEASE = False
ELY_BY_INJECT = "-javaagent:{}=ely.by"
ELY_BY_INJECT_URL = "https://github.com/yushijinhun/authlib-injector/releases/download/v1.2.5/authlib-injector-1.2.5.jar"
MINECRAFT_DIR: str = os.path.join(get_minecraft_directory(), "16launcher")
SKINS_DIR: str = os.path.join(MINECRAFT_DIR, "skins")
RESOURCEPACKS_DIR = os.path.join(MINECRAFT_DIR, "resourcepacks")
SHADERPACKS_DIR = os.path.join(MINECRAFT_DIR, "shaderpacks")
SETTINGS_PATH: str = os.path.join(MINECRAFT_DIR, "settings.json")
LOG_FILE: str = os.path.join(MINECRAFT_DIR, "launcher_log.txt")
NEWS_FILE: str = os.path.join(MINECRAFT_DIR, "launcher_news.json")
ELYBY_API_URL: str = "https://authserver.ely.by/api/"
ELYBY_SKINS_URL: str = "https://skinsystem.ely.by/skins/"
ELYBY_AUTH_URL: str = "https://account.ely.by/oauth2/v1"
# URL для загрузки/изменения скинов (оставьте пустым '', чтобы отключить функционал загрузки скинов)
ELYBY_SKIN_UPLOAD_URL: str = (
    ""  # API для загрузки не существует, используйте https://ely.by/skins
)
ELYBY_TEXTURES_URL: str = "https://skinsystem.ely.by/textures/"
MODS_DIR: str = os.path.join(MINECRAFT_DIR, "mods")
# Используем GitHub вместо Ely.by из-за проблем с SSL-сертификатом
AUTHLIB_INJECTOR_URL: str = (
    "https://api.github.com/repos/yushijinhun/authlib-injector/releases/latest"
)
AUTHLIB_JAR_PATH: str = os.path.join(MINECRAFT_DIR, "authlib-injector.jar")
CLIENT_ID = "16Launcher1"
# Ely.by OAuth2 endpoints - используем единый базовый URL
DEVICE_CODE_URL = f"{ELYBY_AUTH_URL}/device/code"
TOKEN_URL = f"{ELYBY_AUTH_URL}/token"
headers = {"Content-Type": "application/json", "User-Agent": "16Launcher/1.0"}
default_settings = {
    "show_motd": True,
    "language": "ru",
    "close_on_launch": False,
    "memory": 4,
    "minecraft_directory": MINECRAFT_DIR,
    "mods_directory": MODS_DIR,
    "last_username": "",
    "favorites": [],
    "last_version": "",
    "last_loader": "vanilla",
    "show_snapshots": False,
    "auto_install_java": False,
    # Обновления лаунчера
    "check_updates_on_start": True,
    "auto_update": False,
    # Ely.by session data
    "ely_access_token": "",
    "ely_username": "",
    "ely_uuid": "",
    "ely_logged_in": False,
}
adjectives = [
    "Cool",
    "Mighty",
    "Epic",
    "Crazy",
    "Wild",
    "Sneaky",
    "Happy",
    "Angry",
    "Funny",
    "Lucky",
    "Dark",
    "Light",
    "Red",
    "Blue",
    "Green",
    "Golden",
    "Silver",
    "Iron",
    "Diamond",
    "Emerald",
]
nouns = [
    "Player",
    "Gamer",
    "Hero",
    "Villain",
    "Warrior",
    "Miner",
    "Builder",
    "Explorer",
    "Adventurer",
    "Hunter",
    "Wizard",
    "Knight",
    "Ninja",
    "Pirate",
    "Dragon",
    "Wolf",
    "Fox",
    "Bear",
    "Tiger",
    "Ender",
    "Sosun",
]
numbers = ["123", "42", "99", "2023", "777", "1337", "69", "100", "1", "0"]
versions = "versions"
