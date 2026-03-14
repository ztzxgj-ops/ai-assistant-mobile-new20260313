#!/bin/bash

# macOS AI 助理应用 - 快速启动脚本

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="AIAssistant"
SCHEME="AIAssistant"

echo "🚀 启动 AI 个人助理 macOS 应用..."
echo ""

# 检查 Xcode 是否安装
if ! command -v xcodebuild &> /dev/null; then
    echo "❌ 错误: 未找到 Xcode"
    echo "请先安装 Xcode: https://developer.apple.com/xcode/"
    exit 1
fi

echo "✓ Xcode 已安装"

# 打开项目
echo "📂 打开 Xcode 项目..."
open "${PROJECT_DIR}/${PROJECT_NAME}.xcodeproj"

echo ""
echo "✅ 项目已打开！"
echo ""
echo "📝 后续步骤:"
echo "  1. 在 Xcode 中选择 'My Mac' 作为运行目标"
echo "  2. 按 Cmd+R 运行应用"
echo "  3. 使用演示账户登录:"
echo "     用户名: demo"
echo "     密码: demo123"
echo ""
echo "💡 提示:"
echo "  - 可以在 ContentView.swift 中修改代码"
echo "  - 按 Cmd+B 构建项目"
echo "  - 按 Cmd+R 运行应用"
echo ""
