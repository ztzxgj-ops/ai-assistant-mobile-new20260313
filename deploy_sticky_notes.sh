#!/bin/bash
# Mac备忘录功能部署脚本

echo "========================================="
echo "Mac备忘录功能部署"
echo "========================================="

# 服务器信息
SERVER="root@47.109.148.176"
REMOTE_DIR="/var/www/ai-assistant"

echo ""
echo "📦 准备部署文件..."

# 1. 上传新文件
echo "上传 sticky_note_manager.py..."
scp sticky_note_manager.py ${SERVER}:${REMOTE_DIR}/

echo "上传 create_sticky_notes_table.sql..."
scp create_sticky_notes_table.sql ${SERVER}:${REMOTE_DIR}/

# 2. 上传修改的文件
echo "上传 mysql_manager.py..."
scp mysql_manager.py ${SERVER}:${REMOTE_DIR}/

echo ""
echo "📊 在服务器上创建数据库表..."
ssh ${SERVER} "cd ${REMOTE_DIR} && mysql -u ai_assistant -p\$(grep '\"password\"' mysql_config.json | cut -d'\"' -f4) ai_assistant < create_sticky_notes_table.sql"

if [ $? -eq 0 ]; then
    echo "✅ 数据库表创建成功"
else
    echo "⚠️ 数据库表创建失败（可能已存在）"
fi

echo ""
echo "🔄 重启服务..."
ssh ${SERVER} "sudo supervisorctl restart ai-assistant"

if [ $? -eq 0 ]; then
    echo "✅ 服务重启成功"
else
    echo "❌ 服务重启失败"
    exit 1
fi

echo ""
echo "✅ 部署完成！"
echo ""
echo "注意事项："
echo "1. 备忘录功能仅在macOS系统上生效"
echo "2. Linux服务器上会自动禁用备忘录功能"
echo "3. 本地macOS开发环境可以正常使用Notes.app备忘录"
echo ""
