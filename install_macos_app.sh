#!/bin/bash

# macOS 应用安装脚本

APP_PATH="ai-assistant-mobile/build/macos/Build/Products/Release/忘了吗.app"
INSTALL_PATH="/Applications/忘了吗.app"

echo "🍎 开始安装 macOS 应用..."
echo ""

# 检查应用是否存在
if [ ! -d "$APP_PATH" ]; then
    echo "❌ 应用不存在，请先构建:"
    echo "   cd ai-assistant-mobile"
    echo "   flutter build macos --release"
    exit 1
fi

# 检查是否已安装
if [ -d "$INSTALL_PATH" ]; then
    echo "⚠️  应用已存在于 /Applications"
    read -p "是否覆盖? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  删除旧版本..."
        rm -rf "$INSTALL_PATH"
    else
        echo "❌ 安装已取消"
        exit 1
    fi
fi

# 复制应用
echo "📦 复制应用到 /Applications..."
cp -r "$APP_PATH" "$INSTALL_PATH"

if [ $? -eq 0 ]; then
    echo "✅ 安装成功！"
    echo ""
    echo "🚀 启动应用:"
    echo "   open /Applications/忘了吗.app"
    echo ""
    echo "💡 或在 Finder 中打开 /Applications 文件夹，双击 '忘了吗' 应用"
else
    echo "❌ 安装失败"
    exit 1
fi
