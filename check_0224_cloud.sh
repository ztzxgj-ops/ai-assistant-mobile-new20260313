#!/bin/bash
# 查询云端2月24日的数据

echo "🔍 查询云端2月24日的数据..."
echo "=================================="

ssh root@47.109.148.176 << 'EOF'
cd /var/www/ai-assistant

DB_USER=$(grep '"user"' mysql_config.json | cut -d'"' -f4)
DB_PASS=$(grep '"password"' mysql_config.json | cut -d'"' -f4)
DB_NAME=$(grep '"database"' mysql_config.json | cut -d'"' -f4)

USER_ID=6

echo ""
echo "【云端MySQL数据库】"
echo "--------------------------------"

mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SELECT id, title, content, status, created_at
FROM daily_records
WHERE created_at >= '2026-02-24'
ORDER BY created_at DESC;
" 2>/dev/null

EOF

echo ""
echo "✅ 查询完成"
