#!/bin/bash
# 查询云服务器上的用户数据

echo "🔍 连接到云服务器查询用户数据..."
echo "=================================="

ssh root@47.109.148.176 << 'EOF'
cd /var/www/ai-assistant

# 读取数据库配置
DB_USER=$(grep '"user"' mysql_config.json | cut -d'"' -f4)
DB_PASS=$(grep '"password"' mysql_config.json | cut -d'"' -f4)
DB_NAME=$(grep '"database"' mysql_config.json | cut -d'"' -f4)

echo ""
echo "📊 查询用户：俊哥"
echo "=================================="

# 查询用户信息
mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SELECT id, username, storage_mode, storage_mode_selected, created_at
FROM users
WHERE username = '俊哥';
" 2>/dev/null

# 获取用户ID
USER_ID=$(mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -sN -e "SELECT id FROM users WHERE username = '俊哥';" 2>/dev/null)

if [ -n "$USER_ID" ]; then
    echo ""
    echo "📋 查询用户的待办事项（work_tasks表）："
    echo "=================================="

    mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
    SELECT id, title, content, status, priority, due_date, created_at
    FROM work_tasks
    WHERE user_id = $USER_ID
    ORDER BY created_at DESC;
    " 2>/dev/null

    echo ""
    echo "📊 统计信息："
    mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
    SELECT
        COUNT(*) as 总数,
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as 未完成,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as 已完成
    FROM work_tasks
    WHERE user_id = $USER_ID;
    " 2>/dev/null
else
    echo "❌ 未找到用户：俊哥"
fi

EOF

echo ""
echo "✅ 查询完成"
