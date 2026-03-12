#!/bin/bash

# macOS 应用快速启动脚本

APP_PATH="ai-assistant-mobile/build/macos/Build/Products/Release/忘了吗.app"

echo "🍎 启动 macOS 应用..."
echo "📍 应用路径: $APP_PATH"

if [ ! -d "$APP_PATH" ]; then
    echo "❌ 应用不存在，请先构建:"
    echo "   cd ai-assistant-mobile"
    echo "   flutter build macos --release"
    exit 1
fi

# 使用 open 命令启动
open "$APP_PATH"

echo "✅ 应用已启动"
echo "💡 提示: 首次运行可能需要几秒钟加载"
