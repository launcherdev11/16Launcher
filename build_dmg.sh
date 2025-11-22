#!/bin/bash

# Скрипт для создания .dmg пакета для macOS

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

# Конвертируем иконку в .icns формат
if command -v iconutil >/dev/null 2>&1; then
    # Создаем временную директорию для иконки
    mkdir -p temp_icon.iconset
    
    # Конвертируем .ico в разные размеры PNG
    if command -v convert >/dev/null 2>&1; then
        convert assets/icon.ico -resize 16x16 temp_icon.iconset/icon_16x16.png
        convert assets/icon.ico -resize 32x32 temp_icon.iconset/icon_16x16@2x.png
        convert assets/icon.ico -resize 32x32 temp_icon.iconset/icon_32x32.png
        convert assets/icon.ico -resize 64x64 temp_icon.iconset/icon_32x32@2x.png
        convert assets/icon.ico -resize 128x128 temp_icon.iconset/icon_128x128.png
        convert assets/icon.ico -resize 256x256 temp_icon.iconset/icon_128x128@2x.png
        convert assets/icon.ico -resize 256x256 temp_icon.iconset/icon_256x256.png
        convert assets/icon.ico -resize 512x512 temp_icon.iconset/icon_256x256@2x.png
        convert assets/icon.ico -resize 512x512 temp_icon.iconset/icon_512x512.png
        convert assets/icon.ico -resize 1024x1024 temp_icon.iconset/icon_512x512@2x.png
        
        # Создаем .icns файл
        iconutil -c icns temp_icon.iconset -o "${APP_DIR}/Contents/Resources/icon.icns"
        
        # Удаляем временную директорию
        rm -rf temp_icon.iconset
    else
        echo "ImageMagick не найден. Копируем оригинальную иконку..."
        cp assets/icon.ico "${APP_DIR}/Contents/Resources/icon.icns"
    fi
else
    echo "iconutil не найден. Копируем оригинальную иконку..."
    cp assets/icon.ico "${APP_DIR}/Contents/Resources/icon.icns"
fi

# Создаем DMG
echo "Создание DMG..."
DMG_NAME="${APP_NAME}_${APP_VERSION}.dmg"
DMG_TEMP="temp_dmg"

# Создаем временную директорию для DMG
mkdir -p "${DMG_TEMP}"

# Копируем приложение
cp -r "${APP_DIR}" "${DMG_TEMP}/"

# Создаем символическую ссылку на Applications
ln -s /Applications "${DMG_TEMP}/Applications"

# Создаем DMG
hdiutil create -srcfolder "${DMG_TEMP}" -volname "${APP_NAME}" -fs HFS+ -fsargs "-c c=64,a=16,e=16" -format UDRW -size 200m "${DMG_NAME}.temp"

# Монтируем DMG для настройки
MOUNT_POINT=$(hdiutil attach -readwrite -noverify -noautoopen "${DMG_NAME}.temp" | egrep '^/dev/' | sed 1q | awk '{print $3}')

# Настраиваем DMG
echo "Настройка DMG..."
sleep 2

# Устанавливаем размер окна и позицию
osascript << EOF
tell application "Finder"
    tell disk "${APP_NAME}"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {400, 100, 900, 450}
        set theViewOptions to the icon view options of container window
        set arrangement of theViewOptions to not arranged
        set icon size of theViewOptions to 128
        set background picture of theViewOptions to file ".background:background.png"
        make new alias file at container window to POSIX file "/Applications" with properties {name:"Applications"}
        set position of item "${APP_NAME}.app" of container window to {150, 200}
        set position of item "Applications" of container window to {350, 200}
        close
        open
        update without registering applications
        delay 2
    end tell
end tell
EOF

# Синхронизируем
sync

# Размонтируем
hdiutil detach "${MOUNT_POINT}"

# Конвертируем в финальный DMG
hdiutil convert "${DMG_NAME}.temp" -format UDZO -imagekey zlib-level=9 -o "${DMG_NAME}"

# Удаляем временные файлы
rm -rf "${DMG_TEMP}"
rm -f "${DMG_NAME}.temp"
rm -rf "${APP_DIR}"

echo "Готово! Создан DMG: ${DMG_NAME}"
