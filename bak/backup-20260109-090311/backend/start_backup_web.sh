#!/bin/bash
# 启动备份Web工具

cd "$(dirname "$0")"

echo "======================================"
echo "  AI助理备份工具 - Web版启动器"
echo "======================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装Python"
    exit 1
fi

# 检查sshpass
if ! command -v sshpass &> /dev/null; then
    echo "⚠️  警告：未安装 sshpass"
    echo "   安装方法: brew install sshpass"
    echo ""
fi

echo "🚀 启动Web服务器..."
echo "📂 访问地址: http://127.0.0.1:8888"
echo "⏹️  停止服务: 按 Ctrl+C"
echo ""

# 等待2秒后打开浏览器
(sleep 2 && open http://127.0.0.1:8888) &

# 启动服务器
python3 backup_web_server.py
