#!/bin/bash
# Mac应用打包脚本 - 将AI助理打包为独立的.app

set -e  # 遇到错误立即退出

echo "========================================"
echo "AI Personal Assistant - Mac打包工具"
echo "========================================"
echo ""

# 项目根目录
PROJECT_ROOT=$(pwd)
APP_NAME="AI个人助理"
BUNDLE_ID="com.aiassistant.app"
VERSION="1.0.0"

# 输出目录
DIST_DIR="$PROJECT_ROOT/mac_app_dist"
APP_DIR="$DIST_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

echo "📦 步骤1: 检查依赖..."

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python 3"
    echo "请安装Python 3: brew install python3"
    exit 1
fi

# 检查PyInstaller
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "⚠️  未安装PyInstaller，正在安装..."
    pip3 install pyinstaller
fi

echo "✅ 依赖检查完成"
echo ""

echo "📦 步骤2: 清理旧文件..."
rm -rf "$DIST_DIR"
rm -rf build
rm -rf dist
rm -f *.spec
echo "✅ 清理完成"
echo ""

echo "📦 步骤3: 使用PyInstaller打包Python应用..."

# PyInstaller配置
pyinstaller \
    --name="ai-assistant-server" \
    --onefile \
    --windowed \
    --hidden-import=pymysql \
    --hidden-import=pymysql.cursors \
    --add-data="mysql_config.json:." \
    --add-data="ai_config.json:." \
    --add-data="mobile_ui_v5.css:." \
    --add-data="uploads:uploads" \
    --icon="app_icon.icns" \
    --clean \
    assistant_web.py

echo "✅ PyInstaller打包完成"
echo ""

echo "📦 步骤4: 创建.app bundle结构..."

# 创建目录结构
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# 复制可执行文件
cp dist/ai-assistant-server "$MACOS_DIR/"

# 创建Info.plist
cat > "$CONTENTS_DIR/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>zh_CN</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleExecutable</key>
    <string>launcher.sh</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
EOF

# 创建启动脚本
cat > "$MACOS_DIR/launcher.sh" << 'EOF'
#!/bin/bash

# 获取应用目录
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MACOS_DIR="$APP_DIR/MacOS"

# 切换到MacOS目录
cd "$MACOS_DIR"

# 启动Python服务器（后台运行）
./ai-assistant-server &
SERVER_PID=$!

# 等待服务器启动
sleep 3

# 获取端口号（从日志或默认8000）
PORT=8000

# 打开浏览器
open "http://localhost:$PORT"

# 显示通知
osascript -e 'display notification "AI助理已启动，浏览器将自动打开" with title "AI个人助理"'

# 等待服务器进程
wait $SERVER_PID
EOF

chmod +x "$MACOS_DIR/launcher.sh"

# 复制图标（如果存在）
if [ -f "app_icon.icns" ]; then
    cp app_icon.icns "$RESOURCES_DIR/AppIcon.icns"
fi

echo "✅ .app bundle创建完成"
echo ""

echo "📦 步骤5: 复制配置文件模板..."

# 创建配置目录
mkdir -p "$RESOURCES_DIR/config"

# 复制配置文件示例
if [ -f "mysql_config.json" ]; then
    cp mysql_config.json "$RESOURCES_DIR/config/mysql_config.json.example"
fi

if [ -f "ai_config.json" ]; then
    cp ai_config.json "$RESOURCES_DIR/config/ai_config.json.example"
fi

echo "✅ 配置文件复制完成"
echo ""

echo "📦 步骤6: 创建使用说明..."

cat > "$DIST_DIR/使用说明.txt" << 'EOF'
AI个人助理 - 使用说明
======================================

首次使用步骤：
1. 将 AI个人助理.app 拖到"应用程序"文件夹
2. 右键点击应用 -> 选择"打开"（首次运行需要）
3. 配置数据库连接（见下方）

数据库配置：
应用内置了配置文件模板，首次运行会自动创建配置文件在：
~/Library/Application Support/AIAssistant/

你需要编辑：
- mysql_config.json - 数据库连接信息（云服务器MySQL）
- ai_config.json - AI API配置（通义千问）

云端MySQL配置示例：
{
  "host": "你的云服务器IP",
  "port": 3306,
  "user": "ai_assistant",
  "password": "你的数据库密码",
  "database": "ai_assistant",
  "charset": "utf8mb4"
}

使用方法：
1. 双击打开应用
2. 浏览器会自动打开 http://localhost:8000
3. 注册/登录账户即可使用

数据同步：
- 所有数据存储在云端MySQL数据库
- 换设备后，使用相同账户登录即可访问数据
- 支持多设备同时使用

常见问题：
Q: 无法打开应用？
A: 右键点击应用 -> 选择"打开"，并在弹窗中点击"打开"

Q: 浏览器没有自动打开？
A: 手动访问 http://localhost:8000

Q: 如何停止应用？
A: 关闭浏览器标签页，然后在"活动监视器"中结束ai-assistant-server进程

技术支持：
如有问题，请联系开发者
EOF

echo "✅ 使用说明创建完成"
echo ""

echo "========================================"
echo "🎉 打包完成！"
echo "========================================"
echo ""
echo "输出位置: $DIST_DIR"
echo ""
echo "包含文件:"
echo "  - $APP_NAME.app (可执行应用)"
echo "  - 使用说明.txt"
echo ""
echo "下一步:"
echo "1. 测试运行: open '$APP_DIR'"
echo "2. 分发给用户: 将整个 mac_app_dist 文件夹打包为 .dmg"
echo ""
echo "创建DMG安装包:"
echo "  hdiutil create -volname '$APP_NAME' -srcfolder '$DIST_DIR' -ov -format UDZO '$APP_NAME-$VERSION.dmg'"
echo ""
