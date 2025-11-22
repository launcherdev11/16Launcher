#!/usr/bin/env python3

# Скрипт для создания релиза 16Launcher

import os
import sys
import subprocess
import shutil
from datetime import datetime
import zipfile

APP_NAME = "16Launcher"
APP_VERSION = "1.0.3"

def print_status(message):
    print(f"🔧 {message}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def create_release():
    print("=" * 50)
    print(f"🚀 Создание релиза {APP_NAME} v{APP_VERSION}")
    print("=" * 50)
    
    # Создаем папку для релиза
    release_dir = f"release_{APP_VERSION}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(release_dir, exist_ok=True)
    
    print_status("Сборка для Windows...")
    try:
        subprocess.run([sys.executable, "build.py", "--platform", "windows", "--installer"], check=True)
        
        # Копируем Windows файлы
        if os.path.exists("dist/16Launcher.exe"):
            shutil.copy2("dist/16Launcher.exe", f"{release_dir}/16Launcher_Windows.exe")
            print_success("Windows .exe создан")
        
        if os.path.exists("installer_output/16Launcher_Setup.exe"):
            shutil.copy2("installer_output/16Launcher_Setup.exe", f"{release_dir}/16Launcher_Windows_Installer.exe")
            print_success("Windows установщик создан")
            
    except subprocess.CalledProcessError:
        print_error("Ошибка сборки Windows")
    
    print_status("Сборка для Linux...")
    try:
        subprocess.run([sys.executable, "build.py", "--platform", "linux"], check=True)
        
        if os.path.exists("dist/16Launcher"):
            shutil.copy2("dist/16Launcher", f"{release_dir}/16Launcher_Linux")
            print_success("Linux исполняемый файл создан")
            
    except subprocess.CalledProcessError:
        print_error("Ошибка сборки Linux")
    
    print_status("Сборка для macOS...")
    try:
        subprocess.run([sys.executable, "build.py", "--platform", "macos"], check=True)
        
        if os.path.exists("dist/16Launcher"):
            shutil.copytree("dist/16Launcher", f"{release_dir}/16Launcher_macOS.app", dirs_exist_ok=True)
            print_success("macOS приложение создан")
            
    except subprocess.CalledProcessError:
        print_error("Ошибка сборки macOS")
    
    # Создаем README для релиза
    readme_content = f"""# {APP_NAME} v{APP_VERSION}

## Установка

### Windows
- **Простая установка**: Запустите `16Launcher_Windows_Installer.exe`
- **Портативная версия**: Запустите `16Launcher_Windows.exe`

### Linux
1. Сделайте файл исполняемым: `chmod +x 16Launcher_Linux`
2. Запустите: `./16Launcher_Linux`

### macOS
1. Откройте `16Launcher_macOS.app`
2. Если система блокирует запуск, разрешите в настройках безопасности

## Системные требования

- **Windows**: Windows 10/11
- **Linux**: Ubuntu 18.04+, CentOS 7+, или совместимые дистрибутивы
- **macOS**: macOS 10.13+

## Поддержка

- Сайт: https://16launcher.ru
- Discord: [ссылка на Discord]
- Telegram: [ссылка на Telegram]

---
Дата сборки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(f"{release_dir}/README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # Создаем ZIP архив
    zip_name = f"{APP_NAME}_v{APP_VERSION}_Release.zip"
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, release_dir)
                zipf.write(file_path, arc_path)
    
    print_success(f"Релиз создан: {zip_name}")
    print_success(f"Папка релиза: {release_dir}")
    
    # Показываем размеры файлов
    print("\n📊 Размеры файлов:")
    for file in os.listdir(release_dir):
        file_path = os.path.join(release_dir, file)
        if os.path.isfile(file_path):
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            print(f"  {file}: {size_mb:.1f} МБ")
    
    print(f"\n🎉 Релиз готов! Загрузите {zip_name} для распространения.")

if __name__ == "__main__":
    create_release()

