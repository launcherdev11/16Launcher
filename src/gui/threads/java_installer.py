import os
import shutil
import tempfile
import zipfile

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from config import MINECRAFT_DIR


class JavaInstaller(QThread):
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, required_major: int) -> None:
        super().__init__()
        self.required_major = required_major

    def run(self) -> None:
        try:
            self.progress_signal.emit(0, 100, "Поиск JRE...")

            def fetch_assets(image_type: str):
                # Правильный эндпоинт Adoptium: указывается jvm_impl в пути
                url = (
                    f"https://api.adoptium.net/v3/assets/latest/{self.required_major}/hotspot"
                    f"?architecture=x64&os=windows&image_type={image_type}"
                )
                r = requests.get(url, timeout=20)
                if r.status_code == 404:
                    return []
                r.raise_for_status()
                data = r.json()
                return data if isinstance(data, list) else []

            def fetch_binary_zip(image_type: str) -> str | None:
                # Прямой бинарный эндпоинт с archive_type=zip
                url = (
                    f"https://api.adoptium.net/v3/binary/latest/{self.required_major}/ga/windows/x64/"
                    f"{image_type}/hotspot/normal/eclipse?archive_type=zip"
                )
                resp = requests.get(
                    url, stream=True, timeout=30, allow_redirects=True,
                )
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.url

            # 1) Пытаемся получить JRE, 2) иначе JDK
            def pick_zip_package(assets_list):
                for asset in assets_list:
                    bins = asset.get("binaries", []) or []
                    for b in bins:
                        if b.get("os") != "windows":
                            continue
                        if b.get("architecture") not in ("x64", "amd64"):
                            continue
                        p = b.get("package", {}) or {}
                        name = p.get("name", "")
                        # Ищем обычный ZIP-архив (не MSI)
                        if name.lower().endswith(".zip"):
                            return p
                return None

            # Сначала пробуем прямую ссылку через binary endpoint
            image_used = "jre"
            download_url = fetch_binary_zip("jre")
            if not download_url:
                self.progress_signal.emit(
                    0, 100, "JRE (ZIP) не найден, пробуем JDK...",
                )
                image_used = "jdk"
                download_url = fetch_binary_zip("jdk")
            size = 0
            if not download_url:
                # Фолбэк: assets → выбираем ZIP
                assets = fetch_assets("jre")
                image_used = "jre"
                pkg = pick_zip_package(assets)
                if pkg is None:
                    self.progress_signal.emit(
                        0, 100, "JRE (ZIP) не найден, пробуем JDK...",
                    )
                    assets = fetch_assets("jdk")
                    image_used = "jdk"
                    pkg = pick_zip_package(assets)
                if pkg is None:
                    raise RuntimeError("Подходящий архив Java не найден")
                download_url = pkg["link"]
                size = int(pkg.get("size", 0))

            self.progress_signal.emit(
                0, 100, f"Загрузка {image_used.upper()}...",
            )
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip")
            os.close(tmp_fd)
            downloaded = 0
            with requests.get(download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        if size:
                            percent = int(downloaded / size * 100)
                            self.progress_signal.emit(
                                percent,
                                100,
                                f"Загрузка {image_used.upper()}...",
                            )

            target_root = os.path.join(MINECRAFT_DIR, "java")
            os.makedirs(target_root, exist_ok=True)
            target_dir = os.path.join(target_root, f"jre-{self.required_major}")
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            os.makedirs(target_dir, exist_ok=True)

            self.progress_signal.emit(0, 100, "Распаковка...")
            with zipfile.ZipFile(tmp_path) as zf:
                # Архив содержит корневую папку; извлекаем и переносим вовнутрь target_dir
                zf.extractall(target_root)

            # Найдем распакованную директорию (первая с bin/java(.exe))
            unpacked_dir = None
            for name in os.listdir(target_root):
                candidate = os.path.join(target_root, name)
                if not os.path.isdir(candidate):
                    continue
                java_bin = os.path.join(candidate, "bin", "java.exe")
                if os.path.exists(java_bin):
                    unpacked_dir = candidate
                    break

            if not unpacked_dir:
                raise RuntimeError("Не удалось найти java.exe после распаковки")

            # Переместим в target_dir
            if os.path.abspath(unpacked_dir) != os.path.abspath(target_dir):
                # Если target_dir пустая созданная папка — удалим
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir, ignore_errors=True)
                shutil.move(unpacked_dir, target_dir)

            self.progress_signal.emit(100, 100, "Готово")
            self.finished_signal.emit(
                True, f"Java {self.required_major} установлена",
            )
        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка установки Java: {e!s}")
        finally:
            try:
                if "tmp_path" in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
