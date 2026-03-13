#!/bin/bash

# AI Assistant Desktop - Quick Start Script

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "🚀 AI Assistant Desktop - 快速启动"
echo "=================================="

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到 Node.js"
    echo "请访问 https://nodejs.org 安装 Node.js"
    exit 1
fi

echo "✅ Node.js 版本: $(node --version)"
echo "✅ npm 版本: $(npm --version)"

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo ""
    echo "📦 安装依赖..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
fi

echo ""
echo "🎯 启动选项:"
echo "1) 开发模式 (npm run dev)"
echo "2) 构建 DMG (npm run build-dmg)"
echo "3) 构建 ZIP (npm run build-mac)"
echo "4) 退出"
echo ""
read -p "请选择 (1-4): " choice

case $choice in
    1)
        echo "🔧 启动开发模式..."
        npm run dev
        ;;
    2)
        echo "📦 构建 DMG 安装程序..."
        npm run build-dmg
        echo "✅ 构建完成！输出在 dist/ 目录"
        ;;
    3)
        echo "📦 构建 ZIP 包..."
        npm run build-mac
        echo "✅ 构建完成！输出在 dist/ 目录"
        ;;
    4)
        echo "👋 再见！"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac
