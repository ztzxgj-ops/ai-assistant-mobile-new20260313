#!/bin/bash
# 检查数据库中现有的repeat_type值

ssh root@47.109.148.176 << 'ENDSSH'
echo "📊 查询数据库中现有的repeat_type值..."
mysql -u root -p123456 ai_assistant -e "SELECT repeat_type, COUNT(*) as count FROM reminders GROUP BY repeat_type ORDER BY count DESC;"
ENDSSH
