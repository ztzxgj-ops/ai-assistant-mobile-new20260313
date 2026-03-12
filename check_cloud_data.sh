#!/bin/bash
# 查询云端数据库中的目标数据

echo "🔍 查询云端数据库中的目标数据..."
echo "=================================="

ssh root@47.109.148.176 << 'EOF'
cd /var/www/ai-assistant

# 读取数据库配置
DB_USER=$(grep '"user"' mysql_config.json | cut -d'"' -f4)
DB_PASS=$(grep '"password"' mysql_config.json | cut -d'"' -f4)
DB_NAME=$(grep '"database"' mysql_config.json | cut -d'"' -f4)

USER_ID=6

echo ""
echo "📊 查询云端数据库 - 用户ID: $USER_ID"
echo "=================================="

# 查询目标数据
echo ""
echo "🔍 查找目标数据：b222, 本地111, y222, 云端111"
echo "--------------------------------"

mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SELECT id, title, content, status, created_at
FROM work_tasks
WHERE user_id = $USER_ID
AND (title LIKE '%b222%' OR title LIKE '%本地111%' OR title LIKE '%y222%' OR title LIKE '%云端111%')
ORDER BY created_at DESC;
" 2>/dev/null

echo ""
echo "📋 查询 daily_records 表（如果存在）："
echo "--------------------------------"

# 检查是否有daily_records表
TABLE_EXISTS=$(mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -sN -e "
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = '$DB_NAME' AND table_name = 'daily_records';
" 2>/dev/null)

if [ "$TABLE_EXISTS" = "1" ]; then
    mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
    SELECT id, title, content, status, created_at
    FROM daily_records
    WHERE (title LIKE '%b222%' OR title LIKE '%本地111%' OR title LIKE '%y222%' OR title LIKE '%云端111%')
    ORDER BY created_at DESC;
    " 2>/dev/null
else
    echo "   ⚠️ daily_records 表不存在"
fi

echo ""
echo "📊 最近添加的所有数据（最近20条）："
echo "--------------------------------"

mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SELECT id, title, status, created_at
FROM work_tasks
WHERE user_id = $USER_ID
ORDER BY created_at DESC
LIMIT 20;
" 2>/dev/null

EOF

echo ""
echo "✅ 查询完成"
