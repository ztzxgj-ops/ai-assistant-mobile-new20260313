#!/bin/bash

# 查询本地SQLite数据库daily_records表最后10条数据
# 使用方法: ./query_local_daily_records.sh

DB_PATH="$HOME/Library/Containers/com.wanglewang.assistant/Data/Documents/local_databases/ai_assistant_local_32.db"

echo "正在查询本地数据库..."
echo "数据库路径: ${DB_PATH}"
echo "----------------------------------------"

# 检查数据库文件是否存在
if [ ! -f "${DB_PATH}" ]; then
    echo "错误: 数据库文件不存在"
    echo "路径: ${DB_PATH}"
    exit 1
fi

# 执行查询
sqlite3 "${DB_PATH}" << 'ENDSQL'
.headers on
.mode column
.width 8 12 40 12 20 20
SELECT
    id AS '记录ID',
    subcategory_id AS '子分类ID',
    title AS '标题',
    content AS '内容',
    record_date AS '记录日期',
    created_at AS '创建时间'
FROM daily_records
ORDER BY id DESC
LIMIT 10;
ENDSQL

echo "----------------------------------------"
echo "查询完成"
