#!/bin/bash

# Скрипт для создания .pkg установщика для macOS

set -e

APP_NAME="16Launcher"
APP_VERSION="1.0.3"
APP_DESCRIPTION="The best Minecraft launcher"
APP_BUNDLE_ID="ru.16launcher.app"

# Собираем приложение с PyInstaller
echo "Сборка приложения..."
pyinstaller --noconfirm --onedir --windowed --name ${APP_NAME} --icon=assets/icon.ico --add-data "assets:assets" --add-data "src:src" --paths=src --hidden-import=config --hidden-import=gui.main_window --hidden-import=util --hidden-import=PyQt5.sip --collect-all PyQt5 main.py

# Создаем .app bundle
echo "Создание .app bundle..."
APP_DIR="${APP_NAME}.app"
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"

# Копируем исполняемый файл
cp -r dist/${APP_NAME}/* "${APP_DIR}/Contents/MacOS/"

# Создаем Info.plist
cat > "${APP_DIR}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>${APP_BUNDLE_ID}</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleVersion</key>
    <string>${APP_VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>${APP_VERSION}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
EOF

# Копируем иконку
cp assets/icon.ico "${APP_DIR}/Contents/Resources/icon.icns"

# Создаем директорию для пакета
PKG_ROOT="pkg_root"
mkdir -p "${PKG_ROOT}/Applications"

# Копируем приложение
cp -r "${APP_DIR}" "${PKG_ROOT}/Applications/"

# Создаем Distribution.xml
cat > Distribution.xml << EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>${APP_NAME}</title>
    <organization>ru.16launcher</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="false" rootVolumeOnly="true"/>
    <choices-outline>
        <line choice="default">
            <line choice="${APP_BUNDLE_ID}"/>
        </line>
    </choices-outline>
    <choice id="default"/>
    <choice id="${APP_BUNDLE_ID}" visible="false">
        <pkg-ref id="${APP_BUNDLE_ID}"/>
    </choice>
    <pkg-ref id="${APP_BUNDLE_ID}" version="${APP_VERSION}" onConclusion="none">${APP_NAME}.pkg</pkg-ref>
</installer-gui-script>
EOF

# Создаем PackageInfo
cat > PackageInfo << EOF
<?xml version="1.0" encoding="utf-8"?>
<pkg-info format-version="2" identifier="${APP_BUNDLE_ID}" version="${APP_VERSION}" install-location="/Applications" auth="root">
    <payload installKBytes="50000" numberOfFiles="100"/>
    <bundle-version>
        <bundle id="${APP_BUNDLE_ID}" CFBundleIdentifier="${APP_BUNDLE_ID}" path="${APP_NAME}.app" CFBundleVersion="${APP_VERSION}"/>
    </bundle-version>
</pkg-info>
EOF

# Создаем .pkg
echo "Создание .pkg..."
pkgbuild --root "${PKG_ROOT}" --identifier "${APP_BUNDLE_ID}" --version "${APP_VERSION}" --install-location "/Applications" "${APP_NAME}.pkg"

# Создаем финальный установщик
echo "Создание финального установщика..."
PKG_NAME="${APP_NAME}_${APP_VERSION}.pkg"
productbuild --distribution Distribution.xml --package-path . "${PKG_NAME}"

# Очистка
rm -rf "${PKG_ROOT}"
rm -rf "${APP_DIR}"
rm -f Distribution.xml
rm -f PackageInfo
rm -f "${APP_NAME}.pkg"

echo "Готово! Создан установщик: ${PKG_NAME}"
