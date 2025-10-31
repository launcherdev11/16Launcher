import atexit
import os
import sys

# Добавляем путь к модулям СНАЧАЛА
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# ПОТОМ импортируем
from config import LOG_FILE, MINECRAFT_DIR

# Создаём директорию
os.makedirs(MINECRAFT_DIR, exist_ok=True)

import logging

from PyQt5.QtWidgets import QApplication

from discord_rpc import shutdown_discord_rpc
from gui.main_window import MainWindow
from util import setup_directories

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOG_FILE),
    ],
)

if __name__ == "__main__":
    logging.info("Initializing directories")
    setup_directories()

    atexit.register(shutdown_discord_rpc)

    logging.info("Creating application")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
