# Makefile для сборки 16Launcher

APP_NAME = 16Launcher
APP_VERSION = 1.0.3

.PHONY: all windows linux macos clean install-deps help

# По умолчанию собираем для текущей платформы
all:
	@echo "Сборка для текущей платформы..."
	@python3 build.py

# Сборка для Windows
windows:
	@echo "Сборка для Windows..."
	@python3 build.py --platform windows

# Сборка для Linux
linux:
	@echo "Сборка для Linux..."
	@python3 build.py --platform linux

# Сборка для macOS
macos:
	@echo "Сборка для macOS..."
	@python3 build.py --platform macos

# Сборка для всех платформ
all-platforms:
	@echo "Сборка для всех платформ..."
	@python3 build.py --platform all

# Создание установщиков
installer-windows:
	@echo "Создание установщика Windows..."
	@python3 build.py --platform windows --installer

installer-linux:
	@echo "Создание установщика Linux..."
	@python3 build.py --platform linux --installer

installer-macos:
	@echo "Создание установщика macOS..."
	@python3 build.py --platform macos --installer

installer-all:
	@echo "Создание установщиков для всех платформ..."
	@python3 build.py --platform all --installer

# Установка зависимостей
install-deps:
	@echo "Установка зависимостей..."
	pip install PyInstaller PyQt5 requests

# Очистка
clean:
	@echo "Очистка временных файлов..."
	@python3 build.py --clean
	rm -rf dist/
	rm -rf build/
	rm -rf *.spec
	rm -rf __pycache__/
	rm -rf src/__pycache__/
	rm -rf src/gui/__pycache__/
	rm -rf src/gui/threads/__pycache__/
	rm -rf src/gui/widgets/__pycache__/

# Справка
help:
	@echo "Доступные команды:"
	@echo "  make all              - Сборка для текущей платформы"
	@echo "  make windows          - Сборка для Windows"
	@echo "  make linux            - Сборка для Linux"
	@echo "  make macos            - Сборка для macOS"
	@echo "  make all-platforms    - Сборка для всех платформ"
	@echo "  make installer-windows - Создание установщика Windows"
	@echo "  make installer-linux   - Создание установщика Linux"
	@echo "  make installer-macos   - Создание установщика macOS"
	@echo "  make installer-all     - Создание установщиков для всех платформ"
	@echo "  make install-deps      - Установка зависимостей"
	@echo "  make clean             - Очистка временных файлов"
	@echo "  make help              - Показать эту справку"