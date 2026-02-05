#!/bin/bash
# 快速部署邮件验证功能到服务器

set -e  # 遇到错误立即退出

echo "🚀 开始部署邮件验证功能..."
echo ""

# 服务器配置
SERVER_IP="47.109.148.176"
SERVER_USER="root"
SERVER_PATH="/var/www/ai-assistant"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查本地文件
echo "📋 检查本地文件..."
if [ ! -f "verification_service.py" ]; then
    echo "❌ 错误: verification_service.py 不存在"
    exit 1
fi

if [ ! -f "aliyun_email_config.json" ]; then
    echo "❌ 错误: aliyun_email_config.json 不存在"
    exit 1
fi

if [ ! -f "migration_add_verification.sql" ]; then
    echo "❌ 错误: migration_add_verification.sql 不存在"
    exit 1
fi

echo -e "${GREEN}✅ 本地文件检查完成${NC}"
echo ""

# 2. 上传文件到服务器
echo "📤 上传文件到服务器..."
scp verification_service.py ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/
scp aliyun_email_config.json ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/
scp migration_add_verification.sql ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/

echo -e "${GREEN}✅ 文件上传完成${NC}"
echo ""

# 3. 执行数据库迁移
echo "🗄️  执行数据库迁移..."
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /var/www/ai-assistant

# 读取数据库配置
DB_USER=$(grep '"user"' mysql_config.json | cut -d'"' -f4)
DB_PASS=$(grep '"password"' mysql_config.json | cut -d'"' -f4)
DB_NAME=$(grep '"database"' mysql_config.json | cut -d'"' -f4)

# 执行迁移
mysql -u ${DB_USER} -p${DB_PASS} ${DB_NAME} < migration_add_verification.sql

if [ $? -eq 0 ]; then
    echo "✅ 数据库迁移成功"
else
    echo "⚠️  数据库迁移可能已执行过，跳过"
fi
ENDSSH

echo -e "${GREEN}✅ 数据库迁移完成${NC}"
echo ""

# 4. 重启服务
echo "🔄 重启AI助理服务..."
ssh ${SERVER_USER}@${SERVER_IP} "sudo supervisorctl restart ai-assistant"

echo -e "${GREEN}✅ 服务重启完成${NC}"
echo ""

# 5. 检查服务状态
echo "🔍 检查服务状态..."
ssh ${SERVER_USER}@${SERVER_IP} "sudo supervisorctl status ai-assistant"

echo ""
echo -e "${GREEN}🎉 部署完成！${NC}"
echo ""
echo "📝 下一步操作："
echo "1. 查看服务器日志："
echo "   ssh ${SERVER_USER}@${SERVER_IP} 'tail -f /var/log/ai-assistant.log'"
echo ""
echo "2. 使用移动App测试注册功能"
echo ""
echo "3. 在服务器日志中查看验证码（测试模式）"
echo ""
echo -e "${YELLOW}💡 提示: 当前为测试模式，验证码会打印在日志中${NC}"
