#!/bin/bash
# 测试邮件验证码功能

SERVER_URL="http://47.109.148.176/ai"

echo "🧪 开始测试邮件验证码功能..."
echo ""

# 生成随机测试邮箱
TIMESTAMP=$(date +%s)
TEST_EMAIL="test${TIMESTAMP}@example.com"
TEST_USERNAME="testuser${TIMESTAMP}"

echo "📧 测试邮箱: ${TEST_EMAIL}"
echo "👤 测试用户名: ${TEST_USERNAME}"
echo ""

# 1. 发送验证码
echo "1️⃣ 发送验证码..."
RESPONSE=$(curl -s -X POST ${SERVER_URL}/api/verification/send-code \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_type\": \"email\",
    \"contact_value\": \"${TEST_EMAIL}\",
    \"code_type\": \"register\"
  }")

echo "响应: ${RESPONSE}"
echo ""

# 检查是否成功
if echo "${RESPONSE}" | grep -q "success.*true"; then
    echo "✅ 验证码发送成功！"
    echo ""
    echo "📋 请在服务器日志中查看验证码："
    echo "   ssh root@47.109.148.176 'tail -20 /var/log/ai-assistant.log'"
    echo ""
    echo "或者运行以下命令实时查看："
    echo "   ssh root@47.109.148.176 'tail -f /var/log/ai-assistant.log'"
    echo ""

    # 提示用户输入验证码
    echo "🔑 请输入从日志中看到的验证码（6位数字）："
    read -r VERIFICATION_CODE

    if [ -z "${VERIFICATION_CODE}" ]; then
        echo "❌ 未输入验证码，测试终止"
        exit 1
    fi

    echo ""
    echo "2️⃣ 使用验证码注册用户..."

    REGISTER_RESPONSE=$(curl -s -X POST ${SERVER_URL}/api/auth/register-with-verification \
      -H "Content-Type: application/json" \
      -d "{
        \"username\": \"${TEST_USERNAME}\",
        \"password\": \"test123456\",
        \"email\": \"${TEST_EMAIL}\",
        \"verification_code\": \"${VERIFICATION_CODE}\"
      }")

    echo "响应: ${REGISTER_RESPONSE}"
    echo ""

    if echo "${REGISTER_RESPONSE}" | grep -q "success.*true"; then
        echo "✅ 注册成功！"
        echo ""
        echo "🎉 测试完成！邮件验证码功能工作正常。"
    else
        echo "❌ 注册失败，请检查验证码是否正确"
    fi
else
    echo "❌ 验证码发送失败"
    echo "请检查服务器日志: ssh root@47.109.148.176 'tail -50 /var/log/ai-assistant-error.log'"
fi
