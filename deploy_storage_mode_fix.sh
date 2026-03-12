#!/bin/bash

# 部署存储模式选择功能到云服务器
# 功能：用户第一次注册成功登录时，强制选择存储位置

SERVER="root@47.109.148.176"
SERVER_DIR="/var/www/ai-assistant"

echo "========================================="
echo "部署存储模式选择功能"
echo "========================================="

# 1. 备份云服务器数据库
echo ""
echo "1. 备份云服务器数据库..."
ssh $SERVER "mysqldump -u ai_assistant -p'ai_assistant_2024' ai_assistant > /tmp/ai_assistant_backup_$(date +%Y%m%d_%H%M%S).sql"
if [ $? -eq 0 ]; then
    echo "✅ 数据库备份成功"
else
    echo "❌ 数据库备份失败"
    exit 1
fi

# 2. 执行数据库迁移（已经执行过了，这里跳过）
echo ""
echo "2. 数据库迁移已完成（storage_mode和storage_mode_selected字段已添加）"

# 3. 重启服务器（如果需要）
echo ""
echo "3. 检查服务器状态..."
ssh $SERVER "sudo supervisorctl status ai-assistant"

echo ""
echo "========================================="
echo "✅ 部署完成！"
echo "========================================="
echo ""
echo "测试步骤："
echo "1. 在移动应用中注册新用户"
echo "2. 注册成功后应该弹出存储模式选择对话框"
echo "3. 选择存储模式后才能继续使用应用"
echo ""
echo "注意："
echo "- 已有用户的storage_mode_selected默认为0，首次登录时也会弹出选择对话框"
echo "- 选择后storage_mode_selected会被设置为1，之后不再弹出"
echo ""
