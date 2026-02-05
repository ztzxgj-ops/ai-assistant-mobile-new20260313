#!/bin/bash
# FCM推送API端点测试脚本
# 用于测试服务器部署后的API端点

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================="
echo "  FCM推送API端点测试"
echo "========================================="
echo ""

# 服务器配置
SERVER_URL="http://47.109.148.176/ai"

# 检查参数
if [ -z "$1" ]; then
    echo -e "${YELLOW}用法: $0 <用户token>${NC}"
    echo ""
    echo "示例:"
    echo "  $0 your_auth_token_here"
    echo ""
    echo "获取token:"
    echo "  curl -X POST $SERVER_URL/api/auth/login \\"
    echo "    -H \"Content-Type: application/json\" \\"
    echo "    -d '{\"username\":\"your_username\",\"password\":\"your_password\"}'"
    echo ""
    exit 1
fi

USER_TOKEN="$1"

echo "🔑 使用Token: ${USER_TOKEN:0:20}..."
echo ""

# 测试函数
test_api() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"

    echo "-----------------------------------"
    echo "测试: $name"
    echo "端点: $method $endpoint"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" \
            -H "Authorization: Bearer $USER_TOKEN" \
            "$SERVER_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" \
            -X "$method" \
            -H "Authorization: Bearer $USER_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$SERVER_URL$endpoint")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "HTTP状态码: $http_code"

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ 请求成功${NC}"
        echo "响应:"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ 请求失败${NC}"
        echo "响应:"
        echo "$body"
    fi

    echo ""
}

echo "📋 测试1: 注册设备Token"
test_api "注册设备Token" "POST" "/api/device/register-token" '{
    "device_token": "test_fcm_token_'$(date +%s)'",
    "device_type": "ios",
    "device_name": "Test iPhone",
    "device_model": "iPhone 14 Pro",
    "app_version": "1.0.0"
}'

echo "📋 测试2: 获取设备列表"
test_api "获取设备列表" "GET" "/api/device/list" ""

echo "📋 测试3: 测试推送通知"
test_api "测试推送通知" "POST" "/api/device/test-push" ""

echo "📋 测试4: 取消注册设备Token"
# 注意：这需要一个真实的device_token
echo "-----------------------------------"
echo "测试: 取消注册设备Token"
echo "端点: POST /api/device/deactivate-token"
echo -e "${YELLOW}⚠️  需要真实的device_token，跳过此测试${NC}"
echo "手动测试命令:"
echo "curl -X POST $SERVER_URL/api/device/deactivate-token \\"
echo "  -H \"Authorization: Bearer \$USER_TOKEN\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"device_token\":\"your_real_token\"}'"
echo ""

echo "========================================="
echo "  测试完成"
echo "========================================="
echo ""
echo "📝 注意事项："
echo "  1. 如果所有测试都返回401，请检查token是否有效"
echo "  2. 如果返回404，请确认服务器已部署新代码"
echo "  3. 如果返回500，请查看服务器日志"
echo ""
echo "🔍 查看服务器日志："
echo "  ssh root@47.109.148.176 'tail -f /var/log/ai-assistant.log'"
echo ""
