import logging
import sys
import os

from PyQt5.QtWidgets import QApplication, QStyleFactory

src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from config import LOG_FILE
from gui.main_window import MainWindow
from util import setup_directories

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOG_FILE),
    ],
)

if __name__ == '__main__':
    logging.info('Initializing directories')
    setup_directories()
    logging.info('Creating application')
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())