#!/bin/bash
# 在云端服务器上执行 repeat_type 字段迁移

SERVER_IP="47.109.148.176"
SERVER_USER="root"
REMOTE_DIR="/var/www/ai-assistant"

echo "📦 准备迁移文件..."

# 1. 上传迁移脚本到服务器
echo "📤 上传迁移脚本到服务器..."
scp run_repeat_type_migration.py ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/

# 2. 在服务器上执行迁移
echo "🔧 在服务器上执行数据库迁移..."
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /var/www/ai-assistant

echo "📊 执行迁移脚本..."
python3 run_repeat_type_migration.py

if [ $? -eq 0 ]; then
    echo "✅ 数据库迁移成功！"
else
    echo "❌ 数据库迁移失败！"
    exit 1
fi

ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 远程迁移完成！"
    echo ""
    echo "📋 接下来需要："
    echo "  1. 重启服务器上的应用"
    echo "  2. 测试创建 minutely 类型的提醒"
else
    echo "❌ 远程迁移失败！"
    exit 1
fi
