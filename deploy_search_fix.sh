#!/bin/bash
# 部署搜索修复到云服务器

SERVER_IP="47.109.148.176"
SERVER_USER="root"
REMOTE_DIR="/var/www/ai-assistant"

echo "🚀 开始部署搜索修复到云服务器..."
echo "服务器：$SERVER_IP"
echo "目录：$REMOTE_DIR"
echo ""

# 1. 备份远程文件
echo "📦 备份远程文件..."
ssh ${SERVER_USER}@${SERVER_IP} "cp ${REMOTE_DIR}/ai_chat_assistant.py ${REMOTE_DIR}/ai_chat_assistant.py.backup_$(date +%Y%m%d_%H%M%S)"

# 2. 上传修改后的文件
echo "📤 上传修改后的文件..."
scp ai_chat_assistant.py ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/

# 3. 重启服务
echo "🔄 重启AI助理服务..."
ssh ${SERVER_USER}@${SERVER_IP} "supervisorctl restart ai-assistant"

# 4. 验证服务
echo "✅ 验证服务状态..."
ssh ${SERVER_USER}@${SERVER_IP} "supervisorctl status ai-assistant"

echo ""
echo "✅ 部署完成！"
echo "修改已部署到云服务器"
