#!/bin/bash
# 查询特定邮箱的验证码

if [ -z "$1" ]; then
    echo "用法: ./查询邮箱验证码.sh <邮箱地址>"
    echo "示例: ./查询邮箱验证码.sh test@qq.com"
    exit 1
fi

EMAIL="$1"

echo "=================================="
echo "  查询邮箱: $EMAIL"
echo "=================================="
echo ""

ssh root@47.109.148.176 << ENDSSH
mysql -u ai_assistant -p'ai_assistant_2024' -D ai_assistant << ENDSQL
SELECT
    code AS '验证码',
    CASE
        WHEN code_type = 'register' THEN '注册'
        WHEN code_type = 'reset_password' THEN '重置密码'
        ELSE code_type
    END AS '类型',
    CASE
        WHEN used = 1 THEN '已使用'
        WHEN NOW() > expires_at THEN '已过期'
        ELSE '✅ 有效'
    END AS '状态',
    DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS '创建时间',
    DATE_FORMAT(expires_at, '%Y-%m-%d %H:%i:%s') AS '过期时间'
FROM verification_codes
WHERE contact_value = '$EMAIL'
ORDER BY created_at DESC
LIMIT 10;
ENDSQL
ENDSSH

echo ""
echo "=================================="
