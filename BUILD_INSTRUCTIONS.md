# 16Launcher - Инструкции по сборке

## Быстрый старт

### Установка зависимостей
```bash
pip install PyInstaller PyQt5 requests
```

### Сборка для текущей платформы
```bash
python3 build.py
```

### Сборка для всех платформ
```bash
python3 build.py --platform all
```

## Команды PyInstaller для разных платформ

### Windows (.exe)
```bash
pyinstaller --noconfirm --onefile --windowed --name 16Launcher --icon=assets/icon.ico --add-data "assets;assets" --add-data "src;src" --paths=src --hidden-import=config --hidden-import=gui.main_window --hidden-import=util --hidden-import=PyQt5.sip --collect-all PyQt5 main.py
```

### Linux (.bin)
```bash
pyinstaller --noconfirm --onefile --name 16Launcher --icon=assets/icon.ico --add-data "assets:assets" --add-data "src:src" --paths=src --hidden-import=config --hidden-import=gui.main_window --hidden-import=util --hidden-import=PyQt5.sip --collect-all PyQt5 main.py
```

### macOS (.app)
```bash
pyinstaller --noconfirm --onedir --windowed --name 16Launcher --icon=assets/icon.ico --add-data "assets:assets" --add-data "src:src" --paths=src --hidden-import=config --hidden-import=gui.main_window --hidden-import=util --hidden-import=PyQt5.sip --collect-all PyQt5 main.py
```

## Создание установщиков

### Windows (Inno Setup)
1. Установите [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Запустите: `iscc 16Launcher_Setup.iss`
3. Установщик будет создан в папке `installer_output/`

### Linux (.deb пакет)
```bash
chmod +x build_deb.sh
./build_deb.sh
```

### Linux (.rpm пакет)
```bash
chmod +x build_rpm.sh
./build_rpm.sh
```

### macOS (.dmg пакет)
```bash
chmod +x build_dmg.sh
./build_dmg.sh
```

### macOS (.pkg установщик)
```bash
chmod +x build_pkg.sh
./build_pkg.sh
```

## Использование Makefile

### Основные команды
```bash
make all              # Сборка для текущей платформы
make windows          # Сборка для Windows
make linux            # Сборка для Linux
make macos            # Сборка для macOS
make all-platforms    # Сборка для всех платформ
```

### Создание установщиков
```bash
make installer-windows # Установщик Windows
make installer-linux   # Установщики Linux (.deb/.rpm)
make installer-macos   # Установщики macOS (.dmg/.pkg)
make installer-all     # Все установщики
```

### Утилиты
```bash
make install-deps      # Установка зависимостей
make clean             # Очистка временных файлов
make help              # Справка
```

## Структура проекта

```
16Launcher/
├── assets/                 # Ресурсы (иконки, изображения)
├── src/                    # Исходный код
├── config/                 # Конфигурационные файлы
├── dist/                   # Собранные исполняемые файлы
├── installer_output/       # Готовые установщики
├── build.py               # Универсальный скрипт сборки
├── build_deb.sh           # Скрипт для .deb пакета
├── build_rpm.sh           # Скрипт для .rpm пакета
├── build_dmg.sh           # Скрипт для .dmg пакета
├── build_pkg.sh           # Скрипт для .pkg установщика
├── 16Launcher_Setup.iss   # Скрипт Inno Setup для Windows
├── Makefile               # Makefile для удобства
└── main.py                # Точка входа приложения
```

## Требования

### Общие
- Python 3.7+
- PyInstaller
- PyQt5

### Windows
- Inno Setup (для создания установщика)

### Linux
- dpkg-deb (для .deb пакетов)
- rpmbuild (для .rpm пакетов)

### macOS
- Xcode Command Line Tools
- ImageMagick (опционально, для конвертации иконок)

## Решение проблем

### Проблема с иконкой в установщике Windows
Убедитесь, что файл `assets/iconinstall.ico` существует и правильно указан в `16Launcher_Setup.iss`.

### Ошибки сборки на macOS
Убедитесь, что установлены Xcode Command Line Tools:
```bash
xcode-select --install
```

### Ошибки сборки на Linux
Установите необходимые пакеты:
```bash
# Ubuntu/Debian
sudo apt install python3-dev python3-pyqt5-dev

# CentOS/RHEL/Fedora
sudo yum install python3-devel python3-qt5-devel
```

## Автоматизация

Для автоматической сборки всех платформ используйте:
```bash
python3 build.py --platform all --installer
```

Это создаст исполняемые файлы и установщики для всех поддерживаемых платформ.
