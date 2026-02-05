#!/bin/bash
# 部署系统类别清理脚本到云服务器

SERVER="root@47.109.148.176"
SERVER_DIR="/var/www/ai-assistant"

echo "======================================================================"
echo "部署系统类别清理脚本"
echo "======================================================================"
echo ""

# 1. 上传清理脚本
echo "📤 上传清理脚本到服务器..."
scp cleanup_system_categories_simple.py ${SERVER}:${SERVER_DIR}/

if [ $? -ne 0 ]; then
    echo "❌ 上传失败"
    exit 1
fi

echo "✅ 上传成功"
echo ""

# 2. 在服务器上执行
echo "======================================================================"
echo "现在需要在服务器上执行以下命令："
echo "======================================================================"
echo ""
echo "ssh ${SERVER}"
echo "cd ${SERVER_DIR}"
echo ""
echo "# 1. 备份数据库"
echo "mysqldump -u ai_assistant -p ai_assistant > backup_before_cleanup_\$(date +%Y%m%d_%H%M%S).sql"
echo ""
echo "# 2. 运行清理脚本"
echo "python3 cleanup_system_categories_simple.py"
echo ""
echo "# 3. 重启服务"
echo "sudo supervisorctl restart ai-assistant"
echo ""
echo "# 4. 查看日志"
echo "tail -f /var/log/ai-assistant.log"
echo ""
echo "======================================================================"
