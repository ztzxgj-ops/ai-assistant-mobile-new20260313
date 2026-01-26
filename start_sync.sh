#!/bin/bash
# Mac备忘录同步服务启动脚本

echo "========================================="
echo "Mac备忘录同步服务"
echo "========================================="
echo ""

# 检查配置文件
if [ ! -f "sync_config.json" ]; then
    echo "❌ 配置文件不存在"
    echo ""
    echo "请先创建 sync_config.json 文件，内容如下："
    echo ""
    echo '{'
    echo '  "server_url": "http://47.109.148.176/ai/",'
    echo '  "username": "您的用户名",'
    echo '  "password": "您的密码",'
    echo '  "sync_interval": 30'
    echo '}'
    echo ""
    exit 1
fi

# 检查是否已配置用户名密码
username=$(grep '"username"' sync_config.json | cut -d'"' -f4)
if [ -z "$username" ] || [ "$username" = "" ]; then
    echo "❌ 请先配置用户名和密码"
    echo ""
    echo "编辑 sync_config.json 文件，填写您的用户名和密码"
    echo ""
    exit 1
fi

echo "✅ 配置文件检查通过"
echo ""

# 检查依赖
echo "检查Python依赖..."
python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 缺少 requests 库"
    echo ""
    echo "安装命令: pip3 install requests"
    echo ""
    exit 1
fi

echo "✅ 依赖检查通过"
echo ""

# 启动同步服务
echo "启动同步服务..."
echo ""
python3 sync_notes_local.py
