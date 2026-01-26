#!/bin/bash
# 部署"时间类"一级类别到云服务器

SERVER="root@47.109.148.176"
REMOTE_DIR="/var/www/ai-assistant"

echo "=========================================="
echo "部署时间类一级类别"
echo "=========================================="

# 1. 上传SQL脚本
echo "📤 上传SQL脚本..."
scp add_time_category.sql ${SERVER}:${REMOTE_DIR}/

# 2. 上传更新后的category_system.py
echo "📤 上传category_system.py..."
scp category_system.py ${SERVER}:${REMOTE_DIR}/

# 3. 在服务器上执行SQL脚本
echo "🗄️  执行数据库更新..."
ssh ${SERVER} << 'ENDSSH'
cd /var/www/ai-assistant
mysql -u ai_assistant -p$(grep '"password"' mysql_config.json | cut -d'"' -f4) ai_assistant < add_time_category.sql
echo "✅ 数据库更新完成"
ENDSSH

# 4. 重启服务
echo "🔄 重启服务..."
ssh ${SERVER} "sudo supervisorctl restart ai-assistant"

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "验证步骤："
echo "1. 访问 http://47.109.148.176/ai/"
echo "2. 登录后查看类别列表，应该能看到'时间类'"
echo "3. 尝试创建时间规划记录"
