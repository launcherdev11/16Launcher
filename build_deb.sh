#!/bin/bash

# Скрипт для создания .deb пакета для Linux

set -e

APP_NAME="16launcher"
APP_VERSION="1.0.3"
APP_DESCRIPTION="The best Minecraft launcher"
APP_MAINTAINER="16Launcher Team <team@16launcher.ru>"
APP_URL="https://16launcher.ru"

# Создаем директории для пакета
mkdir -p deb_package/DEBIAN
mkdir -p deb_package/usr/bin
mkdir -p deb_package/usr/share/applications
mkdir -p deb_package/usr/share/pixmaps
mkdir -p deb_package/usr/share/${APP_NAME}

# Собираем приложение с PyInstaller
echo "Сборка приложения..."
pyinstaller --noconfirm --onefile --name ${APP_NAME} --icon=assets/icon.ico --add-data "assets:assets" --add-data "src:src" --paths=src --hidden-import=config --hidden-import=gui.main_window --hidden-import=util --hidden-import=PyQt5.sip --collect-all PyQt5 main.py

# Копируем исполняемый файл
cp dist/${APP_NAME} deb_package/usr/bin/

# Создаем .desktop файл
cat > deb_package/usr/share/applications/${APP_NAME}.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=16Launcher
Comment=${APP_DESCRIPTION}
Exec=${APP_NAME}
Icon=${APP_NAME}
Terminal=false
Categories=Game;
StartupNotify=true
EOF

# Копируем иконку
cp assets/icon.ico deb_package/usr/share/pixmaps/${APP_NAME}.ico

# Создаем control файл
cat > deb_package/DEBIAN/control << EOF
Package: ${APP_NAME}
Version: ${APP_VERSION}
Section: games
Priority: optional
Architecture: amd64
Depends: python3, python3-pyqt5, python3-requests
Maintainer: ${APP_MAINTAINER}
Description: ${APP_DESCRIPTION}
 16Launcher - лучший Minecraft лаунчер с отличной оптимизацией и удобным интерфейсом.
 .
 Особенности:
  - Удобный интерфейс
  - Быстрая загрузка
  - Поддержка модов
  - Автоматические обновления
Homepage: ${APP_URL}
EOF

# Создаем postinst скрипт
cat > deb_package/DEBIAN/postinst << EOF
#!/bin/bash
set -e

# Обновляем кэш иконок
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/pixmaps
fi

exit 0
EOF

# Создаем prerm скрипт
cat > deb_package/DEBIAN/prerm << EOF
#!/bin/bash
set -e

# Удаляем ярлыки
rm -f /usr/share/applications/${APP_NAME}.desktop

exit 0
EOF

# Делаем скрипты исполняемыми
chmod +x deb_package/DEBIAN/postinst
chmod +x deb_package/DEBIAN/prerm

# Создаем .deb пакет
echo "Создание .deb пакета..."
dpkg-deb --build deb_package ${APP_NAME}_${APP_VERSION}_amd64.deb

echo "Готово! Создан пакет: ${APP_NAME}_${APP_VERSION}_amd64.deb"

# Очистка
rm -rf deb_package
