#!/bin/bash

# Скрипт для создания .rpm пакета для Linux

set -e

APP_NAME="16launcher"
APP_VERSION="1.0.3"
APP_DESCRIPTION="The best Minecraft launcher"
APP_MAINTAINER="16Launcher Team <team@16launcher.ru>"
APP_URL="https://16launcher.ru"

# Создаем директории для пакета
mkdir -p rpm_package/BUILD
mkdir -p rpm_package/RPMS
mkdir -p rpm_package/SOURCES
mkdir -p rpm_package/SPECS
mkdir -p rpm_package/SRPMS

# Собираем приложение с PyInstaller
echo "Сборка приложения..."
pyinstaller --noconfirm --onefile --name ${APP_NAME} --icon=assets/icon.ico --add-data "assets:assets" --add-data "src:src" --paths=src --hidden-import=config --hidden-import=gui.main_window --hidden-import=util --hidden-import=PyQt5.sip --collect-all PyQt5 main.py

# Подготавливаем файлы
cp dist/${APP_NAME} rpm_package/SOURCES/
cp assets/icon.ico rpm_package/SOURCES/${APP_NAME}.ico

# Создаем .desktop файл
cat > rpm_package/SOURCES/${APP_NAME}.desktop << EOF
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

# Создаем spec файл
cat > rpm_package/SPECS/${APP_NAME}.spec << EOF
Name:           ${APP_NAME}
Version:        ${APP_VERSION}
Release:        1%{?dist}
Summary:        ${APP_DESCRIPTION}

License:        MIT
URL:            ${APP_URL}
Source0:        ${APP_NAME}
Source1:        ${APP_NAME}.ico
Source2:        ${APP_NAME}.desktop

BuildArch:      noarch
Requires:       python3, python3-PyQt5

%description
16Launcher - лучший Minecraft лаунчер с отличной оптимизацией и удобным интерфейсом.

Особенности:
- Удобный интерфейс
- Быстрая загрузка
- Поддержка модов
- Автоматические обновления

%prep
# Ничего не нужно делать

%build
# Ничего не нужно делать

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/pixmaps

install -m 755 %{SOURCE0} %{buildroot}/usr/bin/
install -m 644 %{SOURCE1} %{buildroot}/usr/share/pixmaps/
install -m 644 %{SOURCE2} %{buildroot}/usr/share/applications/

%files
/usr/bin/${APP_NAME}
/usr/share/applications/${APP_NAME}.desktop
/usr/share/pixmaps/${APP_NAME}.ico

%post
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/pixmaps
fi

%postun
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi

%changelog
* $(date '+%a %b %d %Y') ${APP_MAINTAINER} - ${APP_VERSION}-1
- Initial package
EOF

# Создаем RPM пакет
echo "Создание .rpm пакета..."
cd rpm_package
rpmbuild --define "_topdir $(pwd)" -bb SPECS/${APP_NAME}.spec

echo "Готово! Создан пакет: RPMS/noarch/${APP_NAME}-${APP_VERSION}-1.noarch.rpm"

# Очистка
cd ..
rm -rf rpm_package
