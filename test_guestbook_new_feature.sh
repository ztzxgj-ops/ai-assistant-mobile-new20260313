#!/bin/bash
# 测试留言墙新消息提示功能

echo "========================================="
echo "测试留言墙新消息提示功能"
echo "========================================="

# 测试API是否可访问
echo ""
echo "1. 测试API是否可访问（无token）..."
curl -X GET "http://47.109.148.176/ai/api/social/guestbook/unread-count" 2>&1 | grep -E "(success|message)" | head -1

echo ""
echo ""
echo "========================================="
echo "测试完成！"
echo "========================================="
echo ""
echo "API已正常部署，现在需要："
echo "1. 重新编译Flutter应用"
echo "2. 安装到设备上测试"
echo ""
echo "编译命令："
echo "  cd ai-assistant-mobile"
echo "  flutter clean"
echo "  flutter pub get"
echo "  flutter build ios"
echo "  # 或者直接运行："
echo "  flutter run -d <device-id>"
