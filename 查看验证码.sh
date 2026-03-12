#!/bin/bash
# 查看注册验证码脚本

echo "=================================="
echo "  AI助理系统 - 验证码查询工具"
echo "=================================="
echo ""

# 查询最近的验证码
ssh root@47.109.148.176 << 'ENDSSH'
mysql -u ai_assistant -p'ai_assistant_2024' -D ai_assistant << 'ENDSQL'
SELECT
    id AS 'ID',
    contact_value AS '邮箱',
    code AS '验证码',
    CASE
        WHEN code_type = 'register' THEN '注册'
        WHEN code_type = 'reset_password' THEN '重置密码'
        ELSE code_type
    END AS '类型',
    CASE
        WHEN used = 1 THEN '已使用'
        WHEN NOW() > expires_at THEN '已过期'
        ELSE '有效'
    END AS '状态',
    DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS '创建时间',
    DATE_FORMAT(expires_at, '%Y-%m-%d %H:%i:%s') AS '过期时间'
FROM verification_codes
ORDER BY created_at DESC
LIMIT 20;
ENDSQL
ENDSSH

echo ""
echo "=================================="
echo "提示: 验证码有效期为10分钟"
echo "=================================="
