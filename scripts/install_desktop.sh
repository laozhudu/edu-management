#!/usr/bin/env bash
# 安装桌面快捷方式（M5-G1）
# 用法: bash scripts/install_desktop.sh [--user]
# 默认安装到当前用户桌面；--user 仅创建 ~/Desktop/.desktop

set -euo pipefail

APP_NAME="教务管理系统"
EXEC="python3 $(pwd)/main.py"
ICON=""

# 查找图标（若有）
for icon in \
    "$(pwd)/assets/icon.png" \
    "$(pwd)/assets/icon.ico" \
    "$(pwd)/assets/logo.png"; do
    if [ -f "$icon" ]; then
        ICON="$icon"
        break
    fi
done

# 桌面目录
if [ "$1" = "--user" ] || [ -n "${XDG_DESKTOP_DIR:-}" ]; then
    DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
else
    DESKTOP_DIR="$HOME/Desktop"
fi
mkdir -p "$DESKTOP_DIR"

DESKTOP_FILE="$DESKTOP_DIR/edu-management.desktop"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=教务管理系统（PyQt5 桌面端 + FastAPI Web）
Exec=bash -c 'cd $(pwd) && $EXEC'
Icon=${ICON:-applications-education}
Terminal=false
Categories=Education;Office;
StartupNotify=true
EOF
chmod +x "$DESKTOP_FILE"

# 注册到应用菜单（可选）
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cp "$DESKTOP_FILE" "$APPS_DIR/"

echo "✅ 桌面快捷方式已安装: $DESKTOP_FILE"
echo "   应用菜单: $APPS_DIR/edu-management.desktop"
if [ -n "$ICON" ]; then
    echo "   图标: $ICON"
else
    echo "   ⚠ 未找到图标文件，使用默认图标"
fi
