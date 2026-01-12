#!/bin/bash
# 修复文件分类问题的部署脚本

SERVER_IP="47.109.148.176"
SERVER_USER="root"
SERVER_DIR="/var/www/ai-assistant"

echo "========================================="
echo "修复文件分类问题 - 部署脚本"
echo "========================================="
echo ""

# 1. 上传修改后的文件
echo "1. 上传修改后的 mysql_manager.py..."
scp mysql_manager.py ${SERVER_USER}@${SERVER_IP}:${SERVER_DIR}/

if [ $? -ne 0 ]; then
    echo "❌ 上传失败"
    exit 1
fi

echo "✅ 文件上传成功"
echo ""

# 2. 上传修复脚本
echo "2. 上传修复脚本 fix_file_categories.py..."
scp fix_file_categories.py ${SERVER_USER}@${SERVER_IP}:${SERVER_DIR}/

if [ $? -ne 0 ]; then
    echo "❌ 上传失败"
    exit 1
fi

echo "✅ 修复脚本上传成功"
echo ""

# 3. 重启服务
echo "3. 重启 AI 助理服务..."
ssh ${SERVER_USER}@${SERVER_IP} "cd ${SERVER_DIR} && supervisorctl restart ai-assistant"

if [ $? -ne 0 ]; then
    echo "❌ 重启失败"
    exit 1
fi

echo "✅ 服务重启成功"
echo ""

# 4. 运行修复脚本
echo "4. 运行修复脚本更新现有文件的分类..."
echo "   (这可能需要一些时间，取决于文件数量)"
echo ""

ssh ${SERVER_USER}@${SERVER_IP} "cd ${SERVER_DIR} && python3 fix_file_categories.py"

if [ $? -ne 0 ]; then
    echo "⚠️  修复脚本执行失败，但服务已更新"
    echo "   新上传的文件将使用正确的分类"
    exit 1
fi

echo ""
echo "========================================="
echo "✅ 部署完成！"
echo "========================================="
echo ""
echo "修改内容："
echo "  1. 增强了 MIME 类型识别逻辑（支持前缀匹配）"
echo "  2. 更新了现有文件的分类"
echo ""
echo "现在文件应该能正确归类到对应的检索标签中了。"
echo ""
