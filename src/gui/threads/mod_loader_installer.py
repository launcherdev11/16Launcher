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
        """Установка Forge через скачивание установщика с обработкой редиректов"""
        try:
            forge_version = find_forge_version(self.mc_version)
            if not forge_version:
                self.finished_signal.emit(
                    False,
                    f'Forge для {self.mc_version} не найден',
                )
                return
            
            # Различные источники для скачивания установщика
            mirror_sources = [
                {
                    'name': 'Прямая ссылка Forge',
                    'url': f'https://files.minecraftforge.net/net/minecraftforge/forge/{forge_version}/forge-{forge_version}-installer.jar'
                },
                {
                    'name': 'BMCLAPI (основное)',
                    'url': f'https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/{forge_version}/forge-{forge_version}-installer.jar'
                },
                {
                    'name': 'MCBBS Mirror',
                    'url': f'https://download.mcbbs.net/maven/net/minecraftforge/forge/{forge_version}/forge-{forge_version}-installer.jar'
                },
                {
                    'name': 'Tencent Cloud',
                    'url': f'https://mirrors.cloud.tencent.com/forge/maven/net/minecraftforge/forge/{forge_version}/forge-{forge_version}-installer.jar'
                }
            ]
            
            temp_dir = os.path.join(MINECRAFT_DIR, 'temp_forge')
            os.makedirs(temp_dir, exist_ok=True)
            
            installer_path = os.path.join(temp_dir, f'forge-{forge_version}-installer.jar')
            
            downloaded = False
            last_error = None
            
            # Пробуем скачать с разных источников
            for source in mirror_sources:
                try:
                    self.progress_signal.emit(10, 100, f'Пробуем: {source["name"]}')
                    logging.info(f'Пробуем скачать с: {source["url"]}')
                    
                    # Отключаем автоматические редиректы, чтобы контролировать процесс
                    session = requests.Session()
                    # Устанавливаем ограничение на редиректы
                    session.max_redirects = 3
                    # Устанавливаем таймаут
                    session.timeout = (30, 60)  # (connect, read)
                    
                    # Делаем запрос без автоматического следования за редиректами
                    response = session.get(source['url'], stream=True, allow_redirects=False)
                    
                    # Обрабатываем редиректы вручную
                    redirect_count = 0
                    while response.status_code in [301, 302, 303, 307, 308] and redirect_count < 5:
                        redirect_url = response.headers.get('Location')
                        if not redirect_url:
                            break
                        
                        # Проверяем URL редиректа
                        logging.info(f'Редирект {redirect_count+1}: {redirect_url}')
                        
                        # Если редирект ведет на заблокированный домен, пропускаем
                        if 'mirrors.ustc.edu.cn' in redirect_url or 'cernet.edu.cn' in redirect_url:
                            logging.warning(f'Пропускаем редирект на потенциально заблокированный домен: {redirect_url}')
                            break
                        
                        # Следуем за редиректом
                        response = session.get(redirect_url, stream=True, allow_redirects=False)
                        redirect_count += 1
                    
                    # Если после редиректов получили ошибку, пропускаем этот источник
                    if response.status_code != 200:
                        logging.warning(f'Сервер вернул код {response.status_code} для {source["url"]}')
                        continue
                    
                    # Проверяем Content-Type
                    content_type = response.headers.get('Content-Type', '').lower()
                    if not ('application/java-archive' in content_type or 
                            'application/x-java-archive' in content_type or
                            'application/octet-stream' in content_type or
                            content_type.endswith('/jar')):
                        logging.warning(f'Неверный Content-Type: {content_type}')
                        continue
                    
                    # Получаем размер файла
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        expected_size = int(content_length)
                    else:
                        expected_size = None
                    
                    # Скачиваем файл
                    with open(installer_path, 'wb') as f:
                        downloaded_size = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                
                                if expected_size:
                                    progress = int(20 + (downloaded_size / expected_size) * 60)
                                    self.progress_signal.emit(progress, 100, f'Скачивание: {source["name"]}')
                    
                    # Проверяем, что файл скачался полностью
                    file_size = os.path.getsize(installer_path)
                    if expected_size and file_size != expected_size:
                        logging.warning(f'Размер файла не совпадает: ожидалось {expected_size}, получили {file_size}')
                        os.remove(installer_path)
                        continue
                    
                    # Проверяем, что это действительно JAR файл (по сигнатуре)
                    if file_size < 100:  # Слишком маленький для JAR
                        logging.warning(f'Файл слишком маленький: {file_size} байт')
                        os.remove(installer_path)
                        continue
                    
                    # Проверяем сигнатуру JAR/ZIP файла (первые 4 байта)
                    with open(installer_path, 'rb') as f:
                        magic = f.read(4)
                        if magic != b'PK\x03\x04':  # JAR/ZIP сигнатура
                            logging.warning(f'Файл не является JAR: сигнатура {magic.hex()}')
                            os.remove(installer_path)
                            continue
                    
                    downloaded = True
                    logging.info(f'Успешно скачали с {source["name"]}, размер: {file_size} байт')
                    break
                    
                except requests.exceptions.RequestException as e:
                    last_error = f'Ошибка сети для {source["name"]}: {e}'
                    logging.warning(last_error)
                    continue
                except Exception as e:
                    last_error = f'Ошибка при скачивании с {source["name"]}: {e}'
                    logging.warning(last_error)
                    continue
            
            if not downloaded:
                # Если не скачали, попробуем через кэшированный прокси
                try:
                    self.progress_signal.emit(10, 100, 'Пробуем через прокси...')
                    proxy_url = f'https://corsproxy.io/?{urllib.parse.quote(f"https://files.minecraftforge.net/net/minecraftforge/forge/{forge_version}/forge-{forge_version}-installer.jar")}'
                    
                    response = requests.get(proxy_url, stream=True, timeout=60)
                    if response.status_code == 200:
                        with open(installer_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        downloaded = True
                except Exception as e:
                    logging.warning(f'Не удалось через прокси: {e}')
            
            if not downloaded:
                error_msg = 'Не удалось скачать установщик Forge.'
                if last_error:
                    error_msg += f' Последняя ошибка: {last_error}'
                error_msg += '\n\nРекомендации:\n1. Проверьте подключение к интернету\n2. Попробуйте включить VPN\n3. Скачайте установщик вручную'
                raise Exception(error_msg)
            
            # Устанавливаем Minecraft версию, если её нет
            version_dir = os.path.join(MINECRAFT_DIR, 'versions', self.mc_version)
            if not os.path.exists(version_dir):
                self.progress_signal.emit(85, 100, 'Установка Minecraft...')
                try:
                    install_minecraft_version(
                        self.mc_version,
                        MINECRAFT_DIR,
                        callback={
                            'setStatus': lambda text: self.progress_signal.emit(85, 100, text[:100]),
                            'setProgress': lambda value: self.progress_signal.emit(85 + value//10, 100, ''),
                            'setMax': lambda value: None,
                        },
                    )
                except Exception as e:
                    logging.warning(f'Не удалось установить Minecraft: {e}')
            
            # Запускаем установщик Forge
            self.progress_signal.emit(90, 100, 'Запуск установщика Forge...')
            
            # Проверяем Java
            try:
                java_version = subprocess.run(['java', '-version'], capture_output=True, text=True, timeout=10)
                logging.info(f'Java найдена: {java_version.stderr[:100]}')
            except Exception as e:
                raise Exception(f'Java не найдена или не работает: {e}')
            
            # Запускаем установщик
            cmd = ['java', '-jar', installer_path, '--installClient']
            
            # Для Windows добавляем параметры
            if os.name == 'nt':
                cmd.extend(['--installDirectory', MINECRAFT_DIR])
            else:
                cmd.extend(['--target', MINECRAFT_DIR])
            
            logging.info(f'Запускаем команду: {" ".join(cmd)}')
            
            process = subprocess.Popen(
                cmd,
                cwd=MINECRAFT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            
            # Читаем вывод
            output_lines = []
            start_time = time.time()
            timeout = 300  # 5 минут
            
            for line in process.stdout:
                if time.time() - start_time > timeout:
                    process.kill()
                    raise Exception(f'Установщик завис (таймаут {timeout} секунд)')
                
                line = line.strip()
                if line:
                    output_lines.append(line)
                    logging.info(f'Forge установщик: {line}')
                    
                    # Показываем прогресс из вывода
                    if 'Progress' in line or '%' in line or 'Downloading' in line:
                        self.progress_signal.emit(92, 100, f'Установка: {line[:80]}')
            
            # Ждем завершения
            process.wait(timeout=30)
            
            if process.returncode != 0:
                # Пробуем запустить без дополнительных параметров
                self.progress_signal.emit(93, 100, 'Повторная попытка установки...')
                
                simple_cmd = ['java', '-jar', installer_path]
                process2 = subprocess.Popen(
                    simple_cmd,
                    cwd=MINECRAFT_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                
                for line in process2.stdout:
                    line = line.strip()
                    if line:
                        logging.info(f'Forge установщик (вторая попытка): {line}')
                
                process2.wait(timeout=120)
                
                if process2.returncode != 0:
                    error_output = '\n'.join(output_lines[-20:]) if output_lines else 'Нет вывода'
                    raise Exception(f'Установщик завершился с кодом {process2.returncode}:\n{error_output}')
            
            # Проверяем, что Forge установился
            forge_version_dir = os.path.join(MINECRAFT_DIR, 'versions', f'{self.mc_version}-forge-{forge_version.split("-")[-1]}')
            if not os.path.exists(forge_version_dir):
                # Ищем любую версию с forge в названии
                import glob
                forge_dirs = glob.glob(os.path.join(MINECRAFT_DIR, 'versions', f'*forge*'))
                if not forge_dirs:
                    logging.warning(f'Не найдена папка Forge в {forge_version_dir}')
            
            # Очищаем временные файлы
            try:
                if os.path.exists(installer_path):
                    os.remove(installer_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                logging.warning(f'Не удалось очистить временные файлы: {e}')
            
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