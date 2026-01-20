#!/bin/bash
# 部署三种搜索模式到云服务器

SERVER_IP="47.109.148.176"
SERVER_USER="root"
REMOTE_DIR="/var/www/ai-assistant"

echo "🚀 开始部署三种搜索模式到云服务器..."
echo "服务器：$SERVER_IP"
echo "目录：$REMOTE_DIR"
echo ""

# 1. 备份远程文件
echo "📦 备份远程文件..."
ssh ${SERVER_USER}@${SERVER_IP} "cd ${REMOTE_DIR} && cp ai_chat_assistant.py ai_chat_assistant.py.backup_$(date +%Y%m%d_%H%M%S)"

if [ $? -ne 0 ]; then
    echo "❌ 备份失败"
    exit 1
fi

# 2. 上传修改后的文件
echo "📤 上传修改后的文件..."
scp ai_chat_assistant.py ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/

if [ $? -ne 0 ]; then
    echo "❌ 上传失败"
    exit 1
fi

# 3. 重启服务
echo "🔄 重启AI助理服务..."
ssh ${SERVER_USER}@${SERVER_IP} "supervisorctl restart ai-assistant"

if [ $? -ne 0 ]; then
    echo "⚠️ 服务重启可能失败，请检查"
fi

# 4. 验证服务
echo "✅ 验证服务状态..."
ssh ${SERVER_USER}@${SERVER_IP} "supervisorctl status ai-assistant"

echo ""
echo "✅ 部署完成！"
echo "修改已部署到云服务器"
echo ""
echo "📝 修改内容："
echo "  1. 实现三种搜索模式："
echo "     - 纯'X'查询：只搜索分类记录"
echo "     - 'X相关'查询：搜索所有记录（不含聊天记录）"
echo "     - 'X所有'查询：搜索所有记录（含聊天记录）"
echo "  2. 修改_comprehensive_search_related()支持include_chat参数"
echo "  3. 添加纯'X'模式的子类别查询逻辑"
echo ""
