#!/bin/bash

# 查询本地SQLite数据库脚本
# 查询 subcategories 和 daily_records 表的最后10条数据

DB_DIR="$HOME/Library/Containers/com.wanglewang.assistant/Data/Documents/local_databases"

# 找到最新的数据库文件
LATEST_DB=$(ls -t "$DB_DIR"/ai_assistant_local_*.db 2>/dev/null | head -1)

if [ -z "$LATEST_DB" ]; then
    echo "❌ 错误：找不到数据库文件"
    echo "数据库路径：$DB_DIR"
    exit 1
fi

echo "📊 使用数据库：$LATEST_DB"
echo ""

# 查询 subcategories 表
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 subcategories 表 - 最后10条数据"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sqlite3 "$LATEST_DB" << EOF
.mode column
.headers on
SELECT id, name, updated_at FROM subcategories ORDER BY rowid DESC LIMIT 10;
EOF

echo ""
echo ""

# 查询 daily_records 表
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 daily_records 表 - 最后10条数据"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sqlite3 "$LATEST_DB" << EOF
.mode column
.headers on
SELECT id, title as name, updated_at FROM daily_records ORDER BY rowid DESC LIMIT 10;
EOF

echo ""
echo "✅ 查询完成"
