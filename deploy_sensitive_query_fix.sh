#!/bin/bash
# 部署敏感信息查询和提醒延迟功能

echo "========================================="
echo "部署敏感信息查询和提醒延迟功能"
echo "========================================="

SERVER="root@47.109.148.176"
REMOTE_DIR="/var/www/ai-assistant"

echo ""
echo "1. 上传Python后端文件..."
scp ai_chat_assistant.py ${SERVER}:${REMOTE_DIR}/
scp assistant_web.py ${SERVER}:${REMOTE_DIR}/
scp mysql_manager.py ${SERVER}:${REMOTE_DIR}/

echo ""
echo "2. 上传数据库迁移脚本..."
scp migrate_add_pending_query.sql ${SERVER}:${REMOTE_DIR}/

echo ""
echo "3. 执行数据库迁移..."
ssh ${SERVER} << 'EOF'
cd /var/www/ai-assistant
mysql -u ai_assistant -p$(grep '"password"' mysql_config.json | cut -d'"' -f4) ai_assistant < migrate_add_pending_query.sql
echo "✅ 数据库迁移完成"
EOF

echo ""
echo "4. 重启服务..."
ssh ${SERVER} "sudo supervisorctl restart ai-assistant"

echo ""
echo "========================================="
echo "✅ 后端部署完成！"
echo "========================================="
echo ""
echo "现在需要部署Flutter应用："
echo "1. cd ai-assistant-mobile"
echo "2. flutter build ios --release"
echo "3. 通过Xcode安装到设备"
echo ""
