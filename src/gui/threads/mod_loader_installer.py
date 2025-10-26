import json
import logging
import os
import shutil
import subprocess
import traceback
import urllib.request

import requests
from minecraft_launcher_lib.fabric import get_all_minecraft_versions, get_latest_loader_version
from minecraft_launcher_lib.fabric import install_fabric as fabric_install
from minecraft_launcher_lib.forge import find_forge_version, install_forge_version
from PyQt5.QtCore import QThread, pyqtSignal

from config import MINECRAFT_DIR, MINECRAFT_VERSIONS
from util import get_quilt_versions


class ModLoaderInstaller(QThread):
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(
        self,
        loader_type: str,
        version: str,
        mc_version: str | None = None,
    ) -> None:
        super().__init__()
        self.loader_type = loader_type.lower()  # Приводим к нижнему регистру
        self.version = version
        self.mc_version = mc_version

    def run(self):
        try:
            if self.loader_type == 'fabric':
                self.install_fabric()
            elif self.loader_type == 'forge':
                self.install_forge()
            elif self.loader_type == 'optifine':
                self.install_optifine()
            elif self.loader_type == 'quilt':
                self.install_quilt()
            elif self.loader_type == 'neoforge':
                self.install_neoforge()
            elif self.loader_type == 'forgeoptifine':
                self.install_forge_optifine()
            else:
                self.finished_signal.emit(
                    False,
                    f'Неизвестный тип модлоадера: {self.loader_type}',
                )
        except Exception as e:
            self.finished_signal.emit(False, f'Критическая ошибка: {e!s}')
            logging.error(
                f'Ошибка установки {self.loader_type}: {e!s}',
                exc_info=True,
            )

    def install_optifine(self):
        """Установка OptiFine"""
        try:
            # Скачивание установщика
            download_url = f'https://optifine.net/adloadx?f=OptiFine_{self.mc_version}.jar'
            optifine_path = os.path.join(MINECRAFT_DIR, 'OptiFine.jar')

            with requests.get(download_url, stream=True) as r:
                with open(optifine_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)

            # Запуск установщика
            command = ['java', '-jar', optifine_path, '--install', MINECRAFT_DIR]
            subprocess.run(command, check=True)

            self.finished_signal.emit(
                True,
                f'OptiFine для {self.mc_version} установлен!',
            )

        except Exception as e:
            self.finished_signal.emit(False, f'Ошибка установки OptiFine: {e!s}')

    def install_quilt(self):
        try:
            from minecraft_launcher_lib.quilt import install_quilt as quilt_install

            # Получаем последнюю версию лоадера для выбранной версии MC
            quilt_versions = get_quilt_versions(self.mc_version)
            if not quilt_versions:
                raise ValueError(f'Quilt для {self.mc_version} не найден')

            loader_version = quilt_versions[0]['version']

            quilt_install(
                minecraft_version=self.mc_version,
                loader_version=loader_version,
                minecraft_directory=MINECRAFT_DIR,
                callback=self.get_callback(),
            )
            self.finished_signal.emit(
                True,
                f'Quilt {loader_version} для {self.mc_version} установлен!',
            )

        except Exception as e:
            self.finished_signal.emit(False, f'Ошибка установки Quilt: {e!s}')

    def install_fabric(self):
        try:
            # Получаем последнюю версию лоадера
            loader_version = get_latest_loader_version()

            # Создаем профиль Fabric
            fabric_install(
                minecraft_version=self.mc_version,
                minecraft_directory=MINECRAFT_DIR,
                loader_version=loader_version,
            )

            self.finished_signal.emit(
                True,
                f'Fabric {loader_version} для {self.mc_version} установлен!',
            )

        except Exception as e:
            self.finished_signal.emit(False, f'Ошибка установки Fabric: {e!s}')
            logging.exception(f'Fabric install error: {traceback.format_exc()}')

    def _check_internet_connection(self):
        """Проверка соединения с серверами Fabric"""
        try:
            urllib.request.urlopen('https://meta.fabricmc.net', timeout=5)
            return True
        except:
            try:
                urllib.request.urlopen('https://google.com', timeout=5)
                return False  # Есть интернет, но Fabric недоступен
            except:
                return False  # Нет интернета

    def _get_fabric_versions_with_fallback(self):
        """Получение версий с несколькими попытками и резервными методами"""
        versions = []

        # Попытка 1: Официальный API Fabric
        try:
            versions_data = get_all_minecraft_versions()
            if versions_data:
                versions = [v['id'] for v in versions_data if isinstance(v, dict) and 'id' in v]
                if versions:
                    return versions
        except:
            pass

        # Попытка 2: Альтернативный источник (GitHub)
        try:
            with urllib.request.urlopen(
                'https://raw.githubusercontent.com/FabricMC/fabric-meta/main/data/game_versions.json',
            ) as response:
                data = json.loads(response.read().decode())
                versions = [v['version'] for v in data if isinstance(v, dict) and 'version' in v]
                if versions:
                    return versions
        except:
            pass

        try:
            return MINECRAFT_VERSIONS
        except:
            pass

        return []

    @staticmethod
    def find_neoforge_version(mc_version: str):
        """Поиск версии NeoForge для указанной версии MC"""
        response = requests.get(
            'https://maven.neoforged.net/api/maven/versions/releases/net.neoforged/neoforge',
        )
        versions = response.json()['versions']
        for v in versions:
            if mc_version in v:
                return v
        return None

    @staticmethod
    def install_quilt_version(
        minecraft_version: str,
        loader_version: str,
        install_dir: str,
        callback: dict,
    ):
        """Установка Quilt"""
        quilt_profile = {
            'mainClass': 'org.quiltmc.loader.impl.launch.knot.KnotClient',
            'libraries': [
                {
                    'name': f'org.quiltmc:quilt-loader:{loader_version}',
                    'url': 'https://maven.quiltmc.org/repository/release/',
                },
            ],
        }

        # Создание профиля Quilt
        version_dir = os.path.join(
            str(install_dir),
            'versions',
            f'quilt-loader-{loader_version}-{minecraft_version}',
        )
        os.makedirs(version_dir, exist_ok=True)

        with open(
            os.path.join(
                version_dir,
                f'quilt-loader-{loader_version}-{minecraft_version}.json',
            ),
            'w',
        ) as f:
            json.dump(quilt_profile, f)

    def _perform_fabric_installation(self):
        """Выполнение установки с проверкой каждого этапа"""
        # Получаем версию загрузчика
        try:
            loader_version = get_latest_loader_version()
            if not loader_version:
                # Если не получается определить последнюю версию, пробуем конкретную
                loader_version = '0.15.7'  # Актуальная стабильная версия на момент написания
        except:
            loader_version = '0.15.7'

        # Установка
        try:
            fabric_install(
                minecraft_version=self.mc_version,
                minecraft_directory=MINECRAFT_DIR,
                loader_version=loader_version,
                callback=self.get_callback(),
            )
            self.finished_signal.emit(
                True,
                f'Fabric {loader_version} для {self.mc_version} успешно установлен!',
            )
        except Exception as e:
            raise ValueError(f'Ошибка установки: {e!s}')

    def install_forge(self):
        """Установка Forge"""
        try:
            forge_version = find_forge_version(self.mc_version)
            if not forge_version:
                self.finished_signal.emit(
                    False,
                    f'Forge для {self.mc_version} не найден',
                )
                return

            install_forge_version(
                forge_version,
                MINECRAFT_DIR,
                callback=self.get_callback(),
            )
            self.finished_signal.emit(True, f'Forge {forge_version} установлен!')

        except Exception as e:
            self.finished_signal.emit(False, f'Ошибка установки Forge: {e!s}')
            logging.error(f'Forge install failed: {e!s}', exc_info=True)

    def get_callback(self):
        """Генератор callback-функций для отслеживания прогресса"""
        return {
            'setStatus': lambda text: self.progress_signal.emit(0, 100, text),
            'setProgress': lambda value: self.progress_signal.emit(value, 100, ''),
            'setMax': lambda value: self.progress_signal.emit(0, value, ''),
        }