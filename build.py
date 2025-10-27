#!/usr/bin/env python3

# Универсальный скрипт для сборки 16Launcher на всех платформах

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path

APP_NAME = "16Launcher"
APP_VERSION = "1.0.3"

# Цвета для вывода
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

# Функции для вывода сообщений
def print_status(message):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

def print_success(message):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

def print_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

# Проверка зависимостей
def check_dependencies():
    print_status("Проверка зависимостей...")
    
    # Проверяем Python
    if not shutil.which("python3") and not shutil.which("python"):
        print_error("Python не найден!")
        return False
    
    # Проверяем PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print_error("PyInstaller не установлен! Установите: pip install pyinstaller")
        return False
    
    # Проверяем PyQt5
    try:
        import PyQt5
    except ImportError:
        print_error("PyQt5 не установлен! Установите: pip install PyQt5")
        return False
    
    print_success("Все зависимости найдены")
    return True

# Функция сборки для Windows
def build_windows():
    print_status("Сборка для Windows...")
    
    cmd = [
        "pyinstaller", "--noconfirm", "--onefile", "--windowed",
        "--name", APP_NAME, "--icon=assets/icon.ico",
        "--add-data", "assets;assets", "--add-data", "src;src",
        "--paths=src", "--hidden-import=config", "--hidden-import=gui.main_window",
        "--hidden-import=util", "--hidden-import=PyQt5.sip", "--collect-all", "PyQt5",
        "main.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        exe_path = f"dist/{APP_NAME}.exe"
        if os.path.exists(exe_path):
            print_success(f"Windows сборка завершена: {exe_path}")
            return True
        else:
            print_error("Ошибка сборки для Windows")
            return False
    except subprocess.CalledProcessError:
        print_error("Ошибка при сборке для Windows")
        return False

# Функция сборки для Linux
def build_linux():
    print_status("Сборка для Linux...")
    
    cmd = [
        "pyinstaller", "--noconfirm", "--onefile",
        "--name", APP_NAME, "--icon=assets/icon.ico",
        "--add-data", "assets:assets", "--add-data", "src:src",
        "--paths=src", "--hidden-import=config", "--hidden-import=gui.main_window",
        "--hidden-import=util", "--hidden-import=PyQt5.sip", "--collect-all", "PyQt5",
        "main.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        bin_path = f"dist/{APP_NAME}"
        if os.path.exists(bin_path):
            print_success(f"Linux сборка завершена: {bin_path}")
            return True
        else:
            print_error("Ошибка сборки для Linux")
            return False
    except subprocess.CalledProcessError:
        print_error("Ошибка при сборке для Linux")
        return False

# Функция сборки для macOS
def build_macos():
    print_status("Сборка для macOS...")
    
    cmd = [
        "pyinstaller", "--noconfirm", "--onedir", "--windowed",
        "--name", APP_NAME, "--icon=assets/icon.ico",
        "--add-data", "assets:assets", "--add-data", "src:src",
        "--paths=src", "--hidden-import=config", "--hidden-import=gui.main_window",
        "--hidden-import=util", "--hidden-import=PyQt5.sip", "--collect-all", "PyQt5",
        "main.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        app_path = f"dist/{APP_NAME}"
        if os.path.exists(app_path):
            print_success(f"macOS сборка завершена: {app_path}")
            return True
        else:
            print_error("Ошибка сборки для macOS")
            return False
    except subprocess.CalledProcessError:
        print_error("Ошибка при сборке для macOS")
        return False

# Функция создания установщика Windows
def create_windows_installer():
    print_status("Создание установщика Windows...")
    
    # Ищем iscc.exe в стандартных местах
    iscc_paths = [
        "iscc",  # В PATH
        r"C:\Program Files (x86)\Inno Setup 6\iscc.exe",
        r"C:\Program Files\Inno Setup 6\iscc.exe",
        r"C:\Program Files (x86)\Inno Setup 5\iscc.exe",
        r"C:\Program Files\Inno Setup 5\iscc.exe",
    ]
    
    iscc_exe = None
    for path in iscc_paths:
        if shutil.which(path) or os.path.exists(path):
            iscc_exe = path
            break
    
    if iscc_exe:
        try:
            print_status(f"Используем Inno Setup: {iscc_exe}")
            subprocess.run([iscc_exe, "16Launcher_Setup.iss"], check=True)
            if os.path.exists("installer_output/16Launcher_Setup.exe"):
                print_success("Установщик Windows создан: installer_output/16Launcher_Setup.exe")
                return True
            else:
                print_error("Ошибка создания установщика Windows")
                return False
        except subprocess.CalledProcessError as e:
            print_error(f"Ошибка при запуске Inno Setup: {e}")
            return False
    else:
        print_warning("Inno Setup не найден. Пропускаем создание установщика Windows")
        print_warning("Установите Inno Setup с https://jrsoftware.org/isinfo.php")
        return True

# Функция создания установщика Linux
def create_linux_installer():
    print_status("Создание установщика Linux...")
    
    success = True
    
    if os.path.exists("build_deb.sh"):
        try:
            subprocess.run(["bash", "build_deb.sh"], check=True)
            print_success("DEB пакет создан")
        except subprocess.CalledProcessError:
            print_error("Ошибка создания DEB пакета")
            success = False
    else:
        print_warning("Скрипт build_deb.sh не найден")
    
    if os.path.exists("build_rpm.sh"):
        try:
            subprocess.run(["bash", "build_rpm.sh"], check=True)
            print_success("RPM пакет создан")
        except subprocess.CalledProcessError:
            print_error("Ошибка создания RPM пакета")
            success = False
    else:
        print_warning("Скрипт build_rpm.sh не найден")
    
    return success

# Функция создания установщика macOS
def create_macos_installer():
    print_status("Создание установщика macOS...")
    
    success = True
    
    if os.path.exists("build_dmg.sh"):
        try:
            subprocess.run(["bash", "build_dmg.sh"], check=True)
            print_success("DMG пакет создан")
        except subprocess.CalledProcessError:
            print_error("Ошибка создания DMG пакета")
            success = False
    else:
        print_warning("Скрипт build_dmg.sh не найден")
    
    if os.path.exists("build_pkg.sh"):
        try:
            subprocess.run(["bash", "build_pkg.sh"], check=True)
            print_success("PKG пакет создан")
        except subprocess.CalledProcessError:
            print_error("Ошибка создания PKG пакета")
            success = False
    else:
        print_warning("Скрипт build_pkg.sh не найден")
    
    return success

# Очистка временных файлов
def cleanup():
    print_status("Очистка временных файлов...")
    
    dirs_to_clean = [
        "build/", "__pycache__/", "src/__pycache__/",
        "src/gui/__pycache__/", "src/gui/threads/__pycache__/",
        "src/gui/widgets/__pycache__/"
    ]
    
    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
    
    print_success("Очистка завершена")

# Главная функция
def main():
    print("=" * 42)
    print(f"   16Launcher Build Script v{APP_VERSION}")
    print("=" * 42)
    
    parser = argparse.ArgumentParser(description="16Launcher Build Script")
    parser.add_argument("-p", "--platform", choices=["windows", "linux", "macos", "all"],
                       help="Платформа для сборки")
    parser.add_argument("-i", "--installer", action="store_true",
                       help="Создать установщик")
    parser.add_argument("-c", "--clean", action="store_true",
                       help="Очистить временные файлы")
    
    args = parser.parse_args()
    
    # Если платформа не указана, определяем автоматически
    if not args.platform:
        import platform
        system = platform.system().lower()
        if system == "windows":
            args.platform = "windows"
        elif system == "linux":
            args.platform = "linux"
        elif system == "darwin":
            args.platform = "macos"
        else:
            args.platform = "all"
    
    print_status(f"Целевая платформа: {args.platform}")
    
    # Проверяем зависимости
    if not check_dependencies():
        return 1
    
    # Очистка
    if args.clean:
        cleanup()
        return 0
    
    # Сборка
    success = True
    
    if args.platform in ["windows", "all"]:
        if not build_windows():
            success = False
        if args.installer:
            if not create_windows_installer():
                success = False
    
    if args.platform in ["linux", "all"]:
        if not build_linux():
            success = False
        if args.installer:
            if not create_linux_installer():
                success = False
    
    if args.platform in ["macos", "all"]:
        if not build_macos():
            success = False
        if args.installer:
            if not create_macos_installer():
                success = False
    
    if success:
        print_success("Сборка завершена!")
        return 0
    else:
        print_error("Сборка завершена с ошибками!")
        return 1

if __name__ == "__main__":
    sys.exit(main())