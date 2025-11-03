import json
import logging
import os
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request
from glob import glob

import requests
from minecraft_launcher_lib.fabric import get_all_minecraft_versions, get_latest_loader_version
from minecraft_launcher_lib.fabric import install_fabric as fabric_install
from minecraft_launcher_lib.forge import find_forge_version, install_forge_version
from PyQt5.QtCore import QThread, pyqtSignal
from minecraft_launcher_lib.install import install_minecraft_version

from config import MINECRAFT_DIR, MINECRAFT_VERSIONS, MODS_DIR
from util import load_settings

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

    def install_fabric(self):
        try:
            loader_version = get_latest_loader_version()
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
        try:
            urllib.request.urlopen('https://meta.fabricmc.net', timeout=5)
            return True
        except:
            try:
                urllib.request.urlopen('https://google.com', timeout=5)
                return False
            except:
                return False

    def _get_fabric_versions_with_fallback(self):
        versions = []

        try:
            versions_data = get_all_minecraft_versions()
            if versions_data:
                versions = [v['id'] for v in versions_data if isinstance(v, dict) and 'id' in v]
                if versions:
                    return versions
        except:
            pass

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

    def _perform_fabric_installation(self):
        try:
            loader_version = get_latest_loader_version()
            if not loader_version:
                loader_version = '0.15.7'
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

            attempts_left = 3
            last_error: Exception | None = None
            while attempts_left > 0:
                try:
                    install_forge_version(
                        forge_version,
                        MINECRAFT_DIR,
                        callback=self.get_callback(),
                    )
                    self.finished_signal.emit(True, f'Forge {forge_version} установлен!')
                    return
                except Exception as ie:
                    last_error = ie
                    msg = str(ie)
                    lib_path = None
                    try:
                        if 'has the wrong Checksum' in msg:
                            before = msg.split(' has the wrong Checksum')[0]
                            start_idx = before.rfind(': ')
                            candidate = before[start_idx + 2 :] if start_idx != -1 else before
                            if candidate.lower().endswith('.jar'):
                                lib_path = candidate.strip()
                        elif 'WinError 2' in msg or 'file not found' in msg.lower():
                            if '.jar' in msg:
                                candidate = msg.split('.jar')[0] + '.jar'
                                lib_path = candidate[candidate.rfind(' ')+1 :].strip('"')
                    except Exception:
                        lib_path = None

                    # Если нашли файл - удалим и попробуем ещё раз
                    if lib_path and os.path.isabs(lib_path):
                        try:
                            if os.path.exists(lib_path):
                                os.remove(lib_path)
                            # заодно удалим соседний .sha1, если он есть
                            sha1_path = lib_path + '.sha1'
                            if os.path.exists(sha1_path):
                                os.remove(sha1_path)
                            # и каталог, если он пустой
                            parent_dir = os.path.dirname(lib_path)
                            try:
                                if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                                    os.rmdir(parent_dir)
                            except Exception:
                                pass
                        except Exception:
                            # даже если удалить не получилось, всё равно повторим попытку
                            pass

                    attempts_left -= 1
                    if attempts_left == 0:
                        raise

            # если сюда дошли, бросим последний пойманный эксепшн
            if last_error is not None:
                raise last_error

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

    def install_optifine(self):
        """Установка OptiFine как отдельного мода через AutomaticOptifinePatcher.

        - Скачивает скрипт optifine_patcher.py
        - Запускает патчинг для указанной версии Minecraft или конкретной версии OptiFine
        - Перемещает полученный *-MOD.jar в каталог модов выбранной версии
        """
        try:
            if not self.mc_version:
                self.finished_signal.emit(False, 'Не указана версия Minecraft для OptiFine')
                return

            self.progress_signal.emit(5, 100, 'Проверка Java...')
            try:
                subprocess.run(['java', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except Exception:
                self.finished_signal.emit(
                    False,
                    'Java не найдена. Установите Java 17+ и добавьте в PATH.',
                )
                return

            self.progress_signal.emit(10, 100, 'Подготовка окружения...')
            work_dir = os.path.join(MINECRAFT_DIR, 'optifine_patcher')
            os.makedirs(work_dir, exist_ok=True)
            patcher_path = os.path.join(work_dir, 'optifine_patcher.py')

            # Скачиваем скрипт (используем исходник из репозитория)
            self.progress_signal.emit(20, 100, 'Загрузка патчера OptiFine...')
            patcher_url = (
                'https://raw.githubusercontent.com/marvin1099/AutomaticOptifinePatcher/main/optifine_patcher.py'
            )
            try:
                with urllib.request.urlopen(patcher_url) as resp, open(patcher_path, 'wb') as f:
                    shutil.copyfileobj(resp, f)
            except Exception as e:
                self.finished_signal.emit(False, f'Не удалось загрузить патчер: {e!s}')
                return

            # Запускаем патчинг
            self.progress_signal.emit(40, 100, 'Запуск патчинга OptiFine...')
            # Формируем аргументы: если передана конкретная версия OptiFine, используем её
            # иначе используем версию Minecraft, чтобы взять свежий релиз для этой ветки
            download_arg = self.version if self.version else self.mc_version

            # Определяем системный Python (нельзя использовать sys.executable в сборке лаунчера)
            python_cmd = self._resolve_python_command()
            if python_cmd is None:
                self.finished_signal.emit(False, 'Python 3 не найден. Установите Python и добавьте в PATH.')
                return

            def run_patcher(args_with_flags: list[str]) -> tuple[bool, str]:
                cmd_local = [*python_cmd, patcher_path, '-d', download_arg, '-w', work_dir] + args_with_flags
                logging.info('OptiFine patcher command: %s', ' '.join(cmd_local))
                try:
                    proc_local = subprocess.Popen(
                        cmd_local,
                        cwd=work_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True,
                    )
                except Exception as e:
                    return False, f'Не удалось запустить патчер: {e!s}'

                # Читаем поток вывода построчно, пишем в лог и статус, следим за таймаутом бездействия
                last_output_time = time.time()
                INACTIVITY_TIMEOUT = 300  # секунд без вывода (5 минут)
                collected_output: list[str] = []
                detected_exit_code: int | None = None
                try:
                    assert proc_local.stdout is not None
                    for raw in proc_local.stdout:
                        line = raw.rstrip('\n')
                        collected_output.append(line)
                        last_output_time = time.time()
                        if line:
                            logging.debug('[OptiFinePatcher] %s', line)
                            self.progress_signal.emit(50, 100, f'Патчинг: {line[:100]}')
                            # Евристика: строка финала патчера с кодом
                            if 'Done Patching OptiFine with code' in line:
                                # Пробуем вытащить код
                                try:
                                    # пример: "Done Patching OptiFine with code 1 (failure)."
                                    parts = line.split('with code', 1)[1].strip()
                                    code_str = parts.split(' ', 1)[0]
                                    detected_exit_code = int(code_str)
                                except Exception:
                                    detected_exit_code = None
                        # проверка таймаута бездействия
                        if time.time() - last_output_time > INACTIVITY_TIMEOUT:
                            proc_local.kill()
                            return False, 'Патчер завис (нет вывода > 5 минут). Остановлен.'
                    # если увидели финальную строку — используем её код, иначе берём код процесса
                    if detected_exit_code is not None:
                        ret_code = detected_exit_code
                    else:
                        ret_code = proc_local.wait(timeout=30)
                    if ret_code != 0:
                        tail = '\n'.join(collected_output[-30:])
                        return False, f'Патчер завершился с кодом {ret_code}.\n{tail}'
                    return True, '\n'.join(collected_output[-30:])
                except Exception as e:
                    try:
                        proc_local.kill()
                    except Exception:
                        pass
                    return False, f'Ошибка выполнения патчера: {e!s}'

            # Вспомогательный поиск результата
            def _find_result_jar_internal() -> str | None:
                try:
                    mod_jars = [
                        p for p in glob(os.path.join(work_dir, '*.jar')) if p.lower().endswith('-mod.jar')
                    ]
                    if not mod_jars:
                        for root, _dirs, files in os.walk(work_dir):
                            for name in files:
                                if name.lower().endswith('-mod.jar'):
                                    mod_jars.append(os.path.join(root, name))
                    if not mod_jars:
                        return None
                    return max(mod_jars, key=os.path.getmtime)
                except Exception:
                    return None

            # Первая попытка с -m -f (перемещение результата и очистка)
            ok, out = run_patcher(['-m', '-f'])
            if not ok and _find_result_jar_internal() is None:
                logging.warning('Патчер завершился ошибкой, повтор без -m/-f: %s', out)
                # Повторная попытка без перемещения/удаления — иногда помогает на Windows
                ok, out2 = run_patcher([])
                if not ok and _find_result_jar_internal() is None:
                    logging.warning('Повтор без -m/-f не помог, пробуем с перекачкой (-r)')
                    ok, out3 = run_patcher(['-r'])
                    if not ok and _find_result_jar_internal() is None:
                        self.finished_signal.emit(False, out3 or out2 or out)
                        return

            # Ищем полученный *-MOD.jar
            self.progress_signal.emit(70, 100, 'Поиск результата...')
            try:
                mod_jars = [
                    p for p in glob(os.path.join(work_dir, '*.jar')) if p.lower().endswith('-mod.jar')
                ]
                # Если не найдено в корне рабочей папки, попробуем подпапки типа 1.12.2/
                if not mod_jars:
                    for root, _dirs, files in os.walk(work_dir):
                        for name in files:
                            if name.lower().endswith('-mod.jar'):
                                mod_jars.append(os.path.join(root, name))
                if not mod_jars:
                    self.finished_signal.emit(False, 'Не удалось найти результат патчинга (*-MOD.jar)')
                    return
                result_jar = max(mod_jars, key=os.path.getmtime)
            except Exception as e:
                self.finished_signal.emit(False, f'Ошибка поиска результата: {e!s}')
                return

            # Перемещение в mods/<mc_version>
            self.progress_signal.emit(85, 100, 'Перемещение в папку модов...')
            try:
                target_dir = os.path.join(MODS_DIR, self.mc_version)
                os.makedirs(target_dir, exist_ok=True)
                target_path = os.path.join(target_dir, os.path.basename(result_jar))
                shutil.move(result_jar, target_path)
            except Exception as e:
                self.finished_signal.emit(False, f'Не удалось переместить мод: {e!s}')
                return

            # Дополнительно: докачать саму версию Minecraft, если не установлена
            try:
                version_dir = os.path.join(MINECRAFT_DIR, 'versions', self.mc_version)
                if not os.path.exists(version_dir):
                    self.progress_signal.emit(92, 100, 'Загрузка файлов версии Minecraft...')
                    def _set_status(text: str):
                        self.progress_signal.emit(92, 100, text)
                    def _set_progress(value: int):
                        self.progress_signal.emit(min(92 + value // 2, 99), 100, '')
                    def _set_max(value: int):
                        self.progress_signal.emit(92, max(value, 100), '')
                    install_minecraft_version(
                        versionid=self.mc_version,
                        minecraft_directory=MINECRAFT_DIR,
                        callback={
                            'setStatus': _set_status,
                            'setProgress': _set_progress,
                            'setMax': _set_max,
                        },
                    )
            except Exception as e:
                logging.warning('Не удалось докачать версию Minecraft: %s', e)

            self.progress_signal.emit(100, 100, 'Готово')
            self.finished_signal.emit(True, f'OptiFine установлен для {self.mc_version}!')

        except Exception as e:
            self.finished_signal.emit(False, f'Неожиданная ошибка: {e!s}')
            logging.error('OptiFine install failed', exc_info=True)

    def _resolve_python_command(self):
        """Находит системную команду для запуска Python 3.

        Возвращает список argv-префикса (например, ['python'] или ['py', '-3'])
        либо None, если подходящий Python не найден.
        """
        candidates = [
            ['python3'],
            ['python'],
            ['py', '-3'],
            ['py'],
        ]
        for prefix in candidates:
            try:
                test_cmd = [*prefix, '--version']
                res = subprocess.run(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                out = (res.stdout or '').strip().lower()
                if res.returncode == 0 and ('python 3' in out or 'python 3' in (out or '')):
                    return prefix
            except Exception:
                continue
        return None