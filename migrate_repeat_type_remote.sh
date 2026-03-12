#!/bin/bash
# 在云端服务器上执行数据库迁移

echo "🔄 准备在云端服务器执行数据库迁移..."
echo ""

# 上传迁移脚本到服务器
scp migrate_add_every_10_minutes.sql root@47.109.148.176:/tmp/

# 在服务器上执行迁移
ssh root@47.109.148.176 << 'ENDSSH'
echo "📊 执行数据库迁移..."
mysql -u root -p123456 ai_assistant < /tmp/migrate_add_every_10_minutes.sql

if [ $? -eq 0 ]; then
    echo "✅ 数据库迁移成功！"
    echo ""
    echo "验证修改："
    mysql -u root -p123456 ai_assistant -e "SHOW COLUMNS FROM reminders LIKE 'repeat_type';"
else
    echo "❌ 数据库迁移失败"
    exit 1
fi

# 清理临时文件
rm /tmp/migrate_add_every_10_minutes.sql
ENDSSH

echo ""
echo "✅ 迁移完成！现在可以使用'每10分钟'提醒功能了"
