#!/bin/bash
# 调试对话界面未读消息徽章显示问题

echo "========================================="
echo "调试对话界面未读消息徽章"
echo "========================================="

echo ""
echo "问题：抽屉菜单有提示，但对话界面左上角没有数字"
echo ""

echo "可能的原因："
echo "1. _pages 数组没有正确更新"
echo "2. MainChatPage 没有接收到 unreadCount"
echo "3. 徽章组件没有正确渲染"
echo ""

echo "已修复："
echo "✅ 在 _updateTotalUnreadCount() 中重新创建 _pages 数组"
echo "✅ 确保 MainChatPage 获取最新的 unreadCount 值"
echo ""

echo "现在需要："
echo "1. 重新编译 Flutter 应用"
echo "2. 完全关闭旧应用（包括后台）"
echo "3. 安装新版本"
echo "4. 测试功能"
echo ""

echo "编译命令："
echo "  cd ai-assistant-mobile"
echo "  flutter clean"
echo "  flutter pub get"
echo "  flutter run -d <device-id>"
echo ""

echo "调试日志关键字："
echo "  📊 [MainPage] 总未读消息数"
echo "  📬 [MainPage] 新留言检查完成"
echo ""

echo "如果还是不显示，请检查："
echo "1. 查看 Flutter 日志，确认 _totalUnreadCount 的值"
echo "2. 确认 MainChatPage 的 widget.unreadCount 是否有值"
echo "3. 检查 AppBar 的 leading Stack 是否正确渲染"
echo ""

echo "========================================="
