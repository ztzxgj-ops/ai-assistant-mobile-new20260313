#!/bin/bash
# 移动"日记"子类别从"其他类"到"时间类"

SERVER="root@47.109.148.176"
REMOTE_DIR="/var/www/ai-assistant"

echo "=========================================="
echo "移动日记子类别"
echo "=========================================="

# 1. 上传SQL脚本
echo "📤 上传SQL脚本..."
scp move_diary_subcategory.sql ${SERVER}:${REMOTE_DIR}/

# 2. 在服务器上执行SQL脚本
echo "🗄️  执行数据库更新..."
ssh ${SERVER} << 'ENDSSH'
cd /var/www/ai-assistant
mysql -u ai_assistant -p$(grep '"password"' mysql_config.json | cut -d'"' -f4) ai_assistant < move_diary_subcategory.sql
echo "✅ 数据库更新完成"
ENDSSH

# 3. 重启服务
echo "🔄 重启服务..."
ssh ${SERVER} "sudo supervisorctl restart ai-assistant"

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "变更内容："
echo "1. 已从'其他类'删除'日记'子类别"
echo "2. 已在'时间类'添加'日记'子类别"
