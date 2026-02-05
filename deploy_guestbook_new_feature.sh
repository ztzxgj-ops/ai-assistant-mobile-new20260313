#!/bin/bash
# 部署留言墙新消息提示功能

echo "========================================="
echo "部署留言墙新消息提示功能"
echo "========================================="

# 服务器信息
SERVER="root@47.109.148.176"
REMOTE_DIR="/var/www/ai-assistant"

echo ""
echo "1. 在云服务器上执行数据库更新..."
ssh $SERVER "cd $REMOTE_DIR && mysql -u ai_assistant -p\$(grep '\"password\"' mysql_config.json | cut -d'\"' -f4) ai_assistant < /tmp/add_guestbook_view_field.sql"

echo ""
echo "2. 上传SQL脚本到服务器..."
scp add_guestbook_view_field.sql $SERVER:/tmp/

echo ""
echo "3. 执行数据库更新..."
ssh $SERVER "mysql -u ai_assistant -p\$(grep '\"password\"' /var/www/ai-assistant/mysql_config.json | cut -d'\"' -f4) ai_assistant < /tmp/add_guestbook_view_field.sql"

echo ""
echo "4. 上传更新后的后端文件..."
scp assistant_web.py $SERVER:$REMOTE_DIR/

echo ""
echo "5. 重启后端服务..."
ssh $SERVER "supervisorctl restart ai-assistant"

echo ""
echo "6. 检查服务状态..."
ssh $SERVER "supervisorctl status ai-assistant"

echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo ""
echo "注意：Flutter应用需要重新编译和安装到设备上"
echo "请运行: cd ai-assistant-mobile && flutter build ios"
