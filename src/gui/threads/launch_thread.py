# launch_thread.py
import io
import logging
import os
import re
import subprocess
import traceback
import zipfile
from uuid import uuid1
from datetime import datetime

import requests
from minecraft_launcher_lib.command import get_minecraft_command
from minecraft_launcher_lib.fabric import get_latest_loader_version
from minecraft_launcher_lib.forge import find_forge_version
from minecraft_launcher_lib.install import install_minecraft_version
from PyQt5.QtCore import QThread, pyqtSignal
import shlex

from config import AUTHLIB_JAR_PATH, MINECRAFT_DIR, ELYBY_HOST


class LaunchThread(QThread):
    launch_setup_signal = pyqtSignal(str, str, str, int, bool)
    progress_update_signal = pyqtSignal(int, int, str)
    state_update_signal = pyqtSignal(bool)
    close_launcher_signal = pyqtSignal()
    # Новый сигнал логов (строки) — основной для консоли в UI
    log_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.version_id = ''
        self.username = ''
        self.loader_type = 'vanilla'
        self.memory_mb = 4096
        self.close_on_launch = False

        # Стейт для глобального прогресса (если нужен)
        self.current_step = 0
        self.total_steps = 100
        self.progress_step = 0

    def launch_setup(
        self,
        version_id,
        username,
        loader_type,
        memory_mb,
        close_on_launch,
    ):
        self.version_id = version_id
        self.username = username
        self.loader_type = loader_type
        self.memory_mb = memory_mb
        self.close_on_launch = close_on_launch

    def run(self):
        try:
            self.log(f'Starting Minecraft launch process for user: {self.username}')
            self.state_update_signal.emit(True)

            # 1. Определение базовых параметров
            launch_version = self.version_id
            is_legacy = self.is_legacy_version(self.version_id)
            # Рабочая директория — глобальная папка лаунчера
            self.effective_dir = MINECRAFT_DIR
            options = {
                'username': self.username,
                'uuid': str(uuid1()),
                'token': '',
                'jvmArguments': [
                    f'-Xmx{self.memory_mb}M',
                    f'-Xms{min(self.memory_mb // 2, 2048)}M',
                ],
                'launcherName': '16Launcher',
                'launcherVersion': '1.0.3',
                'demo': False,
                'fullscreen': 'false',
            }

            # Добавляем пользовательские JRE аргументы из настроек
            try:
                if hasattr(self.parent_window, 'settings'):
                    raw_args = (self.parent_window.settings or {}).get('jre_args', '') or ''
                    if isinstance(raw_args, str) and raw_args.strip():
                        split_args = shlex.split(raw_args, posix=(os.name != 'nt'))
                        options['jvmArguments'].extend(split_args)
            except Exception:
                logging.exception('Failed to parse custom JRE args; ignoring')

            if hasattr(self.parent_window, 'ely_session') and self.parent_window.ely_session:
                self.log('Applying Ely.by session...')
                options.update(
                    {
                        'username': self.parent_window.ely_session['username'],
                        'uuid': self.parent_window.ely_session['uuid'],
                        'token': self.parent_window.ely_session['token'],
                        'jvmArguments': options['jvmArguments'] + [f'-javaagent:{AUTHLIB_JAR_PATH}={ELYBY_HOST}'],
                    }
                )

            # 3. Определение версии для модлоадеров
            if self.loader_type == 'forge':
                self.log('[Forge] Processing Forge version...')
                forge_version = find_forge_version(self.version_id)
                if not forge_version:
                    raise Exception(f'Forge version for {self.version_id} not found')
                launch_version = f'{self.version_id}-forge-{forge_version.split("-")[-1]}'
                self.log(f'[Forge] Launch version: {launch_version}')

            elif self.loader_type == 'fabric':
                self.log('[Fabric] Processing Fabric version...')
                try:
                    loader_version = get_latest_loader_version()
                    launch_version = f'fabric-loader-{loader_version}-{self.version_id}'
                    self.log(f'[Fabric] Launch version: {launch_version}')
                except Exception as e:
                    raise Exception(f'Fabric loader error: {e!s}')

            elif self.loader_type == 'quilt':
                self.log('[Quilt] Processing Quilt version...')
                from minecraft_launcher_lib.quilt import get_quilt_profile

                profile = get_quilt_profile(self.version_id, self.effective_dir)
                launch_version = profile['version']
                self.log(f'[Quilt] Launch version: {launch_version}')

            elif self.loader_type == 'optifine':
                self.log('[OptiFine] Processing OptiFine version...')
                # Ищем установленный профиль OptiFine для выбранной версии MC
                try:
                    versions_dir = os.path.join(self.effective_dir, 'versions')
                    candidates = []
                    if os.path.isdir(versions_dir):
                        for name in os.listdir(versions_dir):
                            try:
                                if not isinstance(name, str):
                                    continue
                                if self.version_id in name and 'OptiFine' in name:
                                    path = os.path.join(versions_dir, name)
                                    if os.path.isdir(path):
                                        candidates.append((name, os.path.getmtime(path)))
                            except Exception:
                                continue
                    if not candidates:
                        raise Exception('OptiFine profile not found; please install OptiFine for this version')
                    # Берём самый свежий профиль
                    candidates.sort(key=lambda t: t[1], reverse=True)
                    launch_version = candidates[0][0]
                    self.log(f'[OptiFine] Launch version: {launch_version}')
                except Exception as e:
                    raise Exception(f'OptiFine profile resolve error: {e!s}')

            # 4. Патч для legacy версий
            if is_legacy:
                self.log('[Legacy] Applying legacy patch...')
                self.apply_legacy_patch(launch_version)

            # 5. Установка версии если требуется
            self.log(f'[CHECK] Checking version {launch_version}...')
            if not os.path.exists(
                os.path.join(self.effective_dir, 'versions', launch_version),
            ):
                self.log('[INSTALL] Installing version...')
                # используем полноценные функции обратного вызова, чтобы и прогресс и логи приходили в UI
                def set_status(text):
                    # текст этапа установки
                    self.log(f'[INSTALL] {text}')
                    try:
                        self.progress_update_signal.emit(0, 100, text)
                    except Exception:
                        logging.exception('progress emit failed')

                def set_progress(value):
                    # процент текущего шага инсталляции
                    self.log(f'[INSTALL PROGRESS] {value}%')
                    try:
                        self.progress_update_signal.emit(value, 100, '')
                    except Exception:
                        logging.exception('progress emit failed')

                def set_max(value):
                    self.log(f'[INSTALL MAX] {value}')
                    try:
                        self.progress_update_signal.emit(0, value, '')
                    except Exception:
                        logging.exception('progress emit failed')

                install_minecraft_version(
                    version = launch_version,
                    minecraft_directory=self.effective_dir,
                    callback={
                        'setStatus': set_status,
                        'setProgress': set_progress,
                        'setMax': set_max,
                    },
                )

            # 6. Формирование команды запуска
            self.log('[BUILD] Building command...')
            command = get_minecraft_command(
                version=launch_version,
                minecraft_directory=self.effective_dir,
                options=options,
            )

            # Добавляем оптимизационные профили JVM (поверх Xmx/Xms, до пользовательских аргументов уже добавленных выше)
            try:
                settings_obj = getattr(self.parent_window, 'settings', {}) or {}
                preset = settings_obj.get('jre_optimized_profile', 'auto')
                preset_args = []
                if preset in ('auto', 'g1gc'):
                    preset_args = [
                        '-XX:+UseG1GC',
                        '-XX:+UnlockExperimentalVMOptions',
                        '-XX:G1NewSizePercent=20',
                        '-XX:G1ReservePercent=20',
                        '-XX:MaxGCPauseMillis=50',
                        '-XX:G1HeapRegionSize=16M',
                    ]
                elif preset == 'none':
                    preset_args = []
                if preset_args:
                    # Вставляем после первых двух Xmx/Xms
                    insert_pos = 2 if len(command) > 2 else 1
                    # Найдём место среди jvm args: команда обычно начинается с java, затем jvm args до "-cp"
                    try:
                        cp_index = command.index('-cp') if '-cp' in command else 2
                        command = command[:cp_index] + preset_args + command[cp_index:]
                    except Exception:
                        command = command[:insert_pos] + preset_args + command[insert_pos:]
            except Exception:
                logging.exception('Failed to apply optimized JVM preset')

            # Обновлять устаревшие SSL-сертификаты (Windows trust store)
            try:
                settings_obj = getattr(self.parent_window, 'settings', {}) or {}
                if bool(settings_obj.get('update_legacy_ssl', False)):
                    ssl_flag = '-Djavax.net.ssl.trustStoreType=Windows-ROOT'
                    try:
                        cp_index = command.index('-cp') if '-cp' in command else 2
                        command = command[:cp_index] + [ssl_flag] + command[cp_index:]
                    except Exception:
                        command.insert(1, ssl_flag)
            except Exception:
                logging.exception('Failed to apply legacy SSL setting')

            # Пользовательский путь к Java
            try:
                settings_obj = getattr(self.parent_window, 'settings', {}) or {}
                java_mode = settings_obj.get('java_mode', 'recommended')
                java_path = settings_obj.get('java_path', '')
                if java_mode == 'custom' and isinstance(java_path, str) and java_path.strip():
                    command[0] = java_path.strip()
            except Exception:
                logging.exception('Failed to apply custom Java path')

            # Аргументы Minecraft (добавляем в конец)
            try:
                settings_obj = getattr(self.parent_window, 'settings', {}) or {}
                mc_raw = settings_obj.get('mc_args', '') or ''
                if isinstance(mc_raw, str) and mc_raw.strip():
                    mc_parts = shlex.split(mc_raw, posix=(os.name != 'nt'))
                    command = command + mc_parts
            except Exception:
                logging.exception('Failed to append Minecraft args')
            # Обрезаем/маскируем чувствительные части, если нужно — тут просто логим команду
            try:
                command_str = ' '.join(command)
            except Exception:
                command_str = str(command)
            self.log(f'[BUILD] Final command: {command_str}')

            # Команда-обёртка: подставляем %command%
            exec_command = command
            use_shell = False
            try:
                settings_obj = getattr(self.parent_window, 'settings', {}) or {}
                wrapper = settings_obj.get('wrapper_cmd', '') or ''
                if isinstance(wrapper, str) and wrapper.strip():
                    quoted = ' '.join(shlex.quote(p) for p in command)
                    wrapper_str = wrapper.replace('%command%', quoted)
                    exec_command = wrapper_str
                    use_shell = True
                    self.log(f'[BUILD] Wrapper applied: {wrapper_str}')
            except Exception:
                logging.exception('Failed to apply wrapper command')

            # 7. Запуск процесса
            self.log('[LAUNCH] Starting Minecraft process...')
            # Для Windows добавляем флаг CREATE_NO_WINDOW чтобы скрыть консольное окно
            creation_flags = 0
            if os.name == 'nt':  # Windows
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            
            minecraft_process = subprocess.Popen(
                exec_command,
                creationflags=creation_flags,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=use_shell,
            )

            # (опционально) читать stdout/stderr и стримить в лог — сейчас просто сообщение
            self.log('[LAUNCH] Minecraft process started.')

            # 8. Закрытие лаунчера если нужно
            if self.close_on_launch:
                self.log('[LAUNCH] Closing launcher as requested...')
                self.close_launcher_signal.emit()

            self.state_update_signal.emit(False)
            self.log('[LAUNCH] Launch completed successfully')

        except Exception as e:
            err_txt = f'[LAUNCH THREAD ERROR] {e!s}'
            print(err_txt)
            self.log(err_txt)
            logging.exception(f'Launch thread failed: {traceback.format_exc()}')
            self.state_update_signal.emit(False)

    @staticmethod
    def is_legacy_version(version: str):
        """Проверяет, является ли версия старой (до 1.7.5)"""
        try:
            m = re.match(r'(\d+)\.(\d+)\.?(\d+)?', version)
            if not m:
                return False
            major, minor, patch = m.groups()
            if int(major) == 1 and (int(minor) < 7 or (int(minor) == 7 and int(patch or 0) < 5)):
                return True
            return False
        except Exception:
            return False

    def setup_authlib(self, options):
        """Настраивает authlib-injector для новых версий"""
        if not os.path.exists(AUTHLIB_JAR_PATH):
            if not self.download_authlib():
                raise Exception('Failed to download authlib-injector')

        options['jvmArguments'].append(f'-javaagent:{AUTHLIB_JAR_PATH}={ELYBY_HOST}')
        options['jvmArguments'].append(
            '-Dauthlibinjector.yggdrasil.prefetched={...}',
        )

    def download_authlib(self):
        """Скачивает authlib-injector"""
        try:
            self.log('[AUTHLIB] Downloading authlib-injector...')
            response = requests.get(
                'https://maven.ely.by/releases/by/ely/authlib/1.2.0/authlib-1.2.0.jar',
            )  # Актуальная версия
            with open(AUTHLIB_JAR_PATH, 'wb') as f:
                f.write(response.content)
            self.log('[AUTHLIB] Download finished.')
            return True
        except Exception as e:
            logging.exception(f'Authlib download failed: {e!s}')
            self.log(f'[AUTHLIB] Download failed: {e!s}')
            return False

    def apply_legacy_patch(self, version: str):
        """Применяет патч для старых версий"""
        try:
            target_dir = getattr(self, 'effective_dir', MINECRAFT_DIR)
            jar_path = os.path.join(target_dir, 'versions', version, f'{version}.jar')

            if not os.path.exists(jar_path):
                raise Exception('JAR file not found')

            patch_url = 'https://ely.by/load/legacy-patch.jar'  # Пример URL
            self.log('[LEGACY] Downloading patch...')
            patch_data = requests.get(patch_url).content

            with zipfile.ZipFile(jar_path, 'a') as jar:
                with zipfile.ZipFile(io.BytesIO(patch_data)) as patch:
                    for file in patch.namelist():
                        if file.endswith('.class'):
                            jar.writestr(file, patch.read(file))
            self.log('[LEGACY] Patch applied successfully.')
        except Exception as e:
            logging.exception(f'Legacy patch failed: {e!s}')
            self.log(f'[LEGACY] Patch failed: {e!s}')
            # не поднимаем дальше — просто логируем и продолжаем

    def log(self, text: str):
        """Удобный helper для логирования + эмита событий в UI"""
        try:
            ts = datetime.now().strftime('%H:%M:%S')
            safe_text = f'[{ts}] {text}'
            # отправляем в UI
            self.log_signal.emit(text)
            # и в стандартный лог
            logging.info(text)
        except Exception:
            logging.exception('Failed to emit log signal')

    # старые приватные функции для глобального прогресса оставляем (могут быть использованы)
    def _set_status(self, text):
        self.progress_update_signal.emit(self.current_step, self.total_steps, text)

    def _set_progress(self, sub_value: int):
        percent_of_stage = 20
        global_progress = self.progress_step * percent_of_stage + (sub_value * percent_of_stage // 100)
        self.current_step = global_progress
        self.progress_update_signal.emit(self.current_step, self.total_steps, '')

    def _set_max(self, _):  # не нужен для глобального прогресса
        pass
