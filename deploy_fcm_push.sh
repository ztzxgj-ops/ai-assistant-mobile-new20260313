#!/bin/bash
# FCM推送通知功能部署脚本

set -e  # 遇到错误立即退出

echo "========================================="
echo "  FCM推送通知功能部署脚本"
echo "========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 服务器配置
SERVER_USER="root"
SERVER_IP="47.109.148.176"
SERVER_PATH="/var/www/ai-assistant"

# 本地项目路径
LOCAL_PATH="/Users/gj/编程/ai助理new"

echo "📋 部署清单："
echo "  - fcm_push_service.py"
echo "  - mysql_manager.py (已更新)"
echo "  - reminder_scheduler.py (已更新)"
echo "  - assistant_web.py (已更新)"
echo "  - database_device_tokens.sql"
echo "  - firebase_config.json (需要手动配置)"
echo ""

# 检查必要文件
echo "🔍 检查必要文件..."

if [ ! -f "$LOCAL_PATH/fcm_push_service.py" ]; then
    echo -e "${RED}❌ 错误: fcm_push_service.py 不存在${NC}"
    exit 1
fi

if [ ! -f "$LOCAL_PATH/database_device_tokens.sql" ]; then
    echo -e "${RED}❌ 错误: database_device_tokens.sql 不存在${NC}"
    exit 1
fi

if [ ! -f "$LOCAL_PATH/firebase_config.json" ]; then
    echo -e "${YELLOW}⚠️  警告: firebase_config.json 不存在${NC}"
    echo "   请从Firebase控制台下载服务账号JSON文件并重命名为 firebase_config.json"
    read -p "   是否继续部署？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ 文件检查完成${NC}"
echo ""

# 确认部署
echo "🚀 准备部署到服务器: $SERVER_USER@$SERVER_IP:$SERVER_PATH"
read -p "   确认继续？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "部署已取消"
    exit 0
fi

echo ""
echo "📤 开始上传文件..."

# 上传新文件
echo "  上传 fcm_push_service.py..."
scp "$LOCAL_PATH/fcm_push_service.py" "$SERVER_USER@$SERVER_IP:$SERVER_PATH/"

echo "  上传 database_device_tokens.sql..."
scp "$LOCAL_PATH/database_device_tokens.sql" "$SERVER_USER@$SERVER_IP:$SERVER_PATH/"

# 上传更新的文件
echo "  上传 mysql_manager.py..."
scp "$LOCAL_PATH/mysql_manager.py" "$SERVER_USER@$SERVER_IP:$SERVER_PATH/"

echo "  上传 reminder_scheduler.py..."
scp "$LOCAL_PATH/reminder_scheduler.py" "$SERVER_USER@$SERVER_IP:$SERVER_PATH/"

echo "  上传 assistant_web.py..."
scp "$LOCAL_PATH/assistant_web.py" "$SERVER_USER@$SERVER_IP:$SERVER_PATH/"

# 上传Firebase配置文件（如果存在）
if [ -f "$LOCAL_PATH/firebase_config.json" ]; then
    echo "  上传 firebase_config.json..."
    scp "$LOCAL_PATH/firebase_config.json" "$SERVER_USER@$SERVER_IP:$SERVER_PATH/"
fi

echo -e "${GREEN}✅ 文件上传完成${NC}"
echo ""

# 在服务器上执行部署步骤
echo "🔧 在服务器上执行部署步骤..."

ssh "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
set -e

cd /var/www/ai-assistant

echo "  安装firebase-admin..."
pip3 install firebase-admin

echo "  创建数据库表..."
mysql -u ai_assistant -p ai_assistant < database_device_tokens.sql 2>/dev/null || echo "  (表可能已存在，跳过)"

echo "  重启服务..."
sudo supervisorctl restart ai-assistant

echo "  检查服务状态..."
sleep 2
sudo supervisorctl status ai-assistant

ENDSSH

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  ✅ 部署完成！${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "📝 后续步骤："
echo "  1. 确保 firebase_config.json 已正确配置"
echo "  2. 在Firebase控制台配置iOS APNs密钥"
echo "  3. 在Firebase控制台配置Android应用"
echo "  4. 在移动端应用中集成Firebase Messaging"
echo "  5. 测试推送通知功能"
echo ""
echo "🔗 相关文档："
echo "  - FIREBASE_PUSH_SETUP_GUIDE.md"
echo ""
echo "🧪 测试命令："
echo "  curl -X POST http://47.109.148.176/ai/api/device/test-push \\"
echo "    -H \"Authorization: Bearer YOUR_TOKEN\" \\"
echo "    -H \"Content-Type: application/json\""
echo ""
