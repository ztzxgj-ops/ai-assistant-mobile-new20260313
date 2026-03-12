#!/bin/bash

# 查询daily_records表数据（本地+云端）
# 使用方法:
#   ./query_daily_records_simple.sh           # 查询所有用户最近10条
#   ./query_daily_records_simple.sh 6         # 查询用户6最近10条
#   ./query_daily_records_simple.sh 6 20      # 查询用户6最近20条
#   ./query_daily_records_simple.sh all 20    # 查询所有用户最近20条

USER_ID=${1:-all}  # 默认查询所有用户
LIMIT=${2:-10}     # 默认查询10条

if [ "$USER_ID" = "all" ]; then
    echo "========================================"
    echo "查询所有用户的 daily_records 数据"
    echo "========================================"
else
    echo "========================================"
    echo "查询用户 ${USER_ID} 的 daily_records 数据"
    echo "========================================"
fi

# ============================================
# 1. 查询本地SQLite数据库
# ============================================
echo ""
echo "【本地SQLite数据库】"
echo "----------------------------------------"

LOCAL_DB_DIR="$HOME/Library/Containers/com.wanglewang.assistant/Data/Documents/local_databases"

if [ "$USER_ID" = "all" ]; then
    # 查询所有用户的本地数据库
    if [ -d "$LOCAL_DB_DIR" ]; then
        DB_COUNT=$(ls -1 "$LOCAL_DB_DIR"/ai_assistant_local_*.db 2>/dev/null | wc -l)
        if [ $DB_COUNT -gt 0 ]; then
            echo "找到 $DB_COUNT 个本地数据库"
            echo ""

            for db_file in "$LOCAL_DB_DIR"/ai_assistant_local_*.db; do
                db_user_id=$(basename "$db_file" | sed 's/ai_assistant_local_//;s/.db//')
                echo ">>> 用户 $db_user_id:"

                sqlite3 "$db_file" << EOF
.headers on
.mode column
SELECT
    id AS 'ID',
    title AS '标题',
    status AS '状态',
    created_at AS '创建时间'
FROM daily_records
ORDER BY id DESC
LIMIT ${LIMIT};
EOF
                echo ""
            done
        else
            echo "❌ 未找到任何本地数据库"
        fi
    else
        echo "❌ 本地数据库目录不存在"
    fi
else
    # 查询指定用户的本地数据库
    LOCAL_DB="$LOCAL_DB_DIR/ai_assistant_local_${USER_ID}.db"

    if [ -f "$LOCAL_DB" ]; then
        echo "数据库路径: $LOCAL_DB"
        echo ""

        sqlite3 "$LOCAL_DB" << EOF
.headers on
.mode column
SELECT
    id AS 'ID',
    title AS '标题',
    status AS '状态',
    created_at AS '创建时间'
FROM daily_records
ORDER BY id DESC
LIMIT ${LIMIT};
EOF
    else
        echo "❌ 本地数据库不存在"
    fi
fi

# ============================================
# 2. 查询云端MySQL数据库
# ============================================
echo ""
echo "【云端MySQL数据库】"
echo "----------------------------------------"
echo "正在连接服务器 47.109.148.176..."
echo ""

if [ "$USER_ID" = "all" ]; then
    # 查询所有用户
    ssh root@47.109.148.176 bash << ENDSSH
# 读取MySQL密码
DB_PASSWORD=\$(grep -o '"password"[[:space:]]*:[[:space:]]*"[^"]*"' /var/www/ai-assistant/mysql_config.json | cut -d'"' -f4)

# 执行MySQL查询
mysql -u ai_assistant -p"\${DB_PASSWORD}" ai_assistant -e "
SET NAMES utf8mb4;
SELECT
    id AS 'ID',
    user_id AS '用户ID',
    title AS '标题',
    status AS '状态',
    created_at AS '创建时间'
FROM daily_records
ORDER BY id DESC
LIMIT ${LIMIT};
"
ENDSSH
else
    # 查询指定用户
    ssh root@47.109.148.176 bash << ENDSSH
# 读取MySQL密码
DB_PASSWORD=\$(grep -o '"password"[[:space:]]*:[[:space:]]*"[^"]*"' /var/www/ai-assistant/mysql_config.json | cut -d'"' -f4)

# 执行MySQL查询
mysql -u ai_assistant -p"\${DB_PASSWORD}" ai_assistant -e "
SET NAMES utf8mb4;
SELECT
    id AS 'ID',
    title AS '标题',
    status AS '状态',
    created_at AS '创建时间'
FROM daily_records
WHERE user_id = ${USER_ID}
ORDER BY id DESC
LIMIT ${LIMIT};
"
ENDSSH
fi

echo "----------------------------------------"
echo "✅ 查询完成"
