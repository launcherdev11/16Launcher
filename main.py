import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import LOG_FILE, MINECRAFT_DIR

# Создаём директорию для Minecraft и логов если её нет
os.makedirs(MINECRAFT_DIR, exist_ok=True)

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)

from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow
from util import setup_directories

if __name__ == '__main__':
    logging.info('Initializing directories')
    setup_directories()
    logging.info('Creating application')
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
