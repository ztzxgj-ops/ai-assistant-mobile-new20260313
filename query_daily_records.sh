#!/bin/bash

# 查询服务器上daily_records表最后10条数据
# 使用方法: ./query_daily_records.sh

SERVER_IP="47.109.148.176"
SERVER_USER="root"
DB_USER="ai_assistant"
DB_NAME="ai_assistant"
CONFIG_PATH="/var/www/ai-assistant/mysql_config.json"

echo "正在连接服务器 ${SERVER_IP}..."
echo "查询 ${DB_NAME}.daily_records 表最后10条数据..."
echo "----------------------------------------"

# 执行查询
ssh ${SERVER_USER}@${SERVER_IP} bash << 'ENDSSH'
# 读取MySQL密码
DB_PASSWORD=$(grep -o '"password"[[:space:]]*:[[:space:]]*"[^"]*"' /var/www/ai-assistant/mysql_config.json | cut -d'"' -f4)

# 执行MySQL查询
mysql -u ai_assistant -p"${DB_PASSWORD}" ai_assistant -e "
SET NAMES utf8mb4;
SELECT
    id AS '记录ID',
    user_id AS '用户ID',
    content AS '内容',
    created_at AS '创建时间',
    updated_at AS '更新时间'
FROM daily_records
ORDER BY id DESC
LIMIT 10;
"
ENDSSH

echo "----------------------------------------"
echo "查询完成"
