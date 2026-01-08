#!/bin/bash
#############################################
# AI助理系统 - 完整部署脚本（含备份）
# 服务器：47.109.148.176
# 日期：2025-12-10
#############################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
SERVER="47.109.148.176"
SERVER_USER="root"
LOCAL_DIR="/Users/jry/gj/ai助理/xyMac"
REMOTE_DIR="/var/www/ai-assistant"
BACKUP_DIR="/root/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo ""
echo "=========================================="
echo "   AI助理系统 - 完整部署脚本"
echo "=========================================="
echo ""
echo -e "${BLUE}服务器：${NC}$SERVER"
echo -e "${BLUE}本地目录：${NC}$LOCAL_DIR"
echo -e "${BLUE}远程目录：${NC}$REMOTE_DIR"
echo ""

# 步骤1：备份云服务器现有系统
echo ""
echo -e "${GREEN}=========================================="
echo "  步骤1：备份云服务器智能鱼缸系统"
echo "==========================================${NC}"
echo ""

echo -e "${YELLOW}正在SSH连接服务器...${NC}"
echo ""

ssh ${SERVER_USER}@${SERVER} << 'BACKUP_EOF'
#!/bin/bash

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/root/backups"

echo "创建备份目录..."
mkdir -p $BACKUP_DIR

echo ""
echo "========== 备份智能鱼缸系统 =========="

# 查找鱼缸系统目录
FISH_TANK_DIR=""
for dir in /var/www/fish-tank /var/www/html /var/www/fishtank /var/www/smart-fish; do
    if [ -d "$dir" ]; then
        FISH_TANK_DIR="$dir"
        break
    fi
done

if [ -z "$FISH_TANK_DIR" ]; then
    echo "尝试查找包含index.html的目录..."
    FISH_TANK_DIR=$(find /var/www -name "index.html" -type f 2>/dev/null | head -1 | xargs dirname)
fi

if [ -n "$FISH_TANK_DIR" ] && [ -d "$FISH_TANK_DIR" ]; then
    echo "找到鱼缸系统目录: $FISH_TANK_DIR"
    BACKUP_FILE="$BACKUP_DIR/fish-tank_${TIMESTAMP}.tar.gz"
    echo "正在备份到: $BACKUP_FILE"
    tar -czf "$BACKUP_FILE" -C "$(dirname $FISH_TANK_DIR)" "$(basename $FISH_TANK_DIR)"
    echo "✅ 鱼缸系统备份完成: $(du -h $BACKUP_FILE | cut -f1)"
else
    echo "⚠️ 未找到鱼缸系统目录"
    echo "正在列出 /var/www 目录内容..."
    ls -la /var/www/ 2>/dev/null || echo "/var/www 目录不存在"
fi

echo ""
echo "========== 备份Nginx配置 =========="
if [ -f /etc/nginx/nginx.conf ]; then
    cp /etc/nginx/nginx.conf "$BACKUP_DIR/nginx.conf_${TIMESTAMP}"
    echo "✅ nginx.conf 已备份"
fi

if [ -d /etc/nginx/sites-available ]; then
    tar -czf "$BACKUP_DIR/nginx-sites_${TIMESTAMP}.tar.gz" -C /etc/nginx sites-available sites-enabled 2>/dev/null
    echo "✅ Nginx站点配置已备份"
fi

if [ -d /etc/nginx/conf.d ]; then
    tar -czf "$BACKUP_DIR/nginx-conf.d_${TIMESTAMP}.tar.gz" -C /etc/nginx conf.d 2>/dev/null
    echo "✅ Nginx conf.d已备份"
fi

echo ""
echo "========== 备份完成 =========="
echo "备份文件列表："
ls -lh $BACKUP_DIR/*${TIMESTAMP}* 2>/dev/null || echo "无备份文件"
echo ""
BACKUP_EOF

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ 备份过程中出现错误${NC}"
    echo -e "${YELLOW}请检查SSH连接和服务器权限${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ 步骤1完成：云服务器备份已创建${NC}"

# 步骤2：上传AI助理系统文件
echo ""
echo -e "${GREEN}=========================================="
echo "  步骤2：上传AI助理系统文件"
echo "==========================================${NC}"
echo ""

# 创建远程目录
echo "创建远程目录..."
ssh ${SERVER_USER}@${SERVER} "mkdir -p ${REMOTE_DIR}"

# 上传文件（排除不必要的文件）
echo "正在上传文件..."
rsync -avz --progress \
    --exclude='.git' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.DS_Store' \
    --exclude='server.log' \
    --exclude='*.log' \
    --exclude='backup_*' \
    --exclude='私人助理v*' \
    --exclude='node_modules' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='ai-assistant-electron/dist' \
    --exclude='ai-assistant-electron/node_modules' \
    --exclude='ai-assistant-mobile' \
    --exclude='bak' \
    --exclude='ai-assistant-backup-*' \
    --exclude='*.zip' \
    --exclude='*.dmg' \
    --exclude='*.pkg' \
    --exclude='*.app' \
    "${LOCAL_DIR}/" "${SERVER_USER}@${SERVER}:${REMOTE_DIR}/"

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ 文件上传失败${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ 步骤2完成：文件上传成功${NC}"

# 步骤3：执行远程部署
echo ""
echo -e "${GREEN}=========================================="
echo "  步骤3：执行自动部署脚本"
echo "==========================================${NC}"
echo ""

ssh ${SERVER_USER}@${SERVER} << 'DEPLOY_EOF'
#!/bin/bash

cd /var/www/ai-assistant

echo "========== 安装系统依赖 =========="
if command -v dnf &> /dev/null; then
    dnf install -y python3 python3-pip supervisor mysql curl wget
elif command -v apt &> /dev/null; then
    apt update -qq
    apt install -y python3 python3-pip supervisor mysql-client curl wget
fi

echo ""
echo "========== 安装Python依赖 =========="
pip3 install --quiet pymysql

echo ""
echo "========== 设置目录权限 =========="
mkdir -p /var/www/ai-assistant/uploads/avatars
mkdir -p /var/www/ai-assistant/uploads/images

# 检测Web服务器用户 (nginx 或 www-data)
WEB_USER="www-data"
if id "nginx" &>/dev/null; then
    WEB_USER="nginx"
elif id "apache" &>/dev/null; then
    WEB_USER="apache"
fi
echo "使用Web用户: $WEB_USER"

chown -R $WEB_USER:$WEB_USER /var/www/ai-assistant
chmod -R 755 /var/www/ai-assistant
chmod -R 775 /var/www/ai-assistant/uploads

# 设置配置文件权限
if [ -f /var/www/ai-assistant/mysql_config.json ]; then
    chmod 600 /var/www/ai-assistant/mysql_config.json
    chown $WEB_USER:$WEB_USER /var/www/ai-assistant/mysql_config.json
fi

if [ -f /var/www/ai-assistant/ai_config.json ]; then
    chmod 600 /var/www/ai-assistant/ai_config.json
    chown $WEB_USER:$WEB_USER /var/www/ai-assistant/ai_config.json
fi

echo ""
echo "========== 配置Supervisor =========="
# 检测Supervisor配置目录
SUPERVISOR_CONF_DIR="/etc/supervisor/conf.d"
SUPERVISOR_EXT=".conf"

if [ -d "/etc/supervisord.d" ]; then
    SUPERVISOR_CONF_DIR="/etc/supervisord.d"
    SUPERVISOR_EXT=".ini"
fi

TARGET_CONF="$SUPERVISOR_CONF_DIR/ai-assistant$SUPERVISOR_EXT"
echo "Supervisor配置路径: $TARGET_CONF"

cp /var/www/ai-assistant/deploy/supervisor-config.conf "$TARGET_CONF"
# 修改运行用户
sed -i "s/user=www-data/user=$WEB_USER/g" "$TARGET_CONF"

# 启动Supervisor服务
systemctl enable --now supervisord 2>/dev/null || systemctl enable --now supervisor

# 重载Supervisor
supervisorctl reread
supervisorctl update

echo ""
echo "========== 显示当前Nginx配置 =========="
echo "当前Nginx配置文件内容（供参考）："
echo "---"
cat /etc/nginx/sites-available/default 2>/dev/null || cat /etc/nginx/nginx.conf | head -50
echo "---"
echo ""
echo "⚠️ 请手动合并AI助理的Nginx配置！"
echo "配置模板位于: /var/www/ai-assistant/deploy/nginx-config.conf"
echo ""

echo "========== 启动AI助理服务 =========="
supervisorctl start ai-assistant 2>/dev/null || supervisorctl restart ai-assistant

echo ""
echo "========== 检查服务状态 =========="
echo ""
echo "Supervisor状态："
supervisorctl status ai-assistant

echo ""
echo "端口监听情况："
lsof -i :8000 | head -5 || netstat -tlnp | grep 8000

echo ""
echo "========== 部署完成 =========="
DEPLOY_EOF

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ 部署过程中出现错误${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ 步骤3完成：自动部署脚本执行完成${NC}"

# 步骤4：验证部署
echo ""
echo -e "${GREEN}=========================================="
echo "  步骤4：验证部署"
echo "==========================================${NC}"
echo ""

echo "测试AI助理服务（本地端口8000）..."
ssh ${SERVER_USER}@${SERVER} "curl -s http://localhost:8000/ | head -5"

echo ""
echo "=========================================="
echo -e "${GREEN}  🎉 部署完成！${NC}"
echo "=========================================="
echo ""
echo "访问地址："
echo "  - 智能鱼缸：http://${SERVER}/"
echo "  - AI助理：  http://${SERVER}:8000/ (临时直接访问)"
echo ""
echo -e "${YELLOW}⚠️ 重要提醒：${NC}"
echo "  1. 请手动配置Nginx反向代理，使AI助理可以通过 /ai/ 路径访问"
echo "  2. 配置模板：/var/www/ai-assistant/deploy/nginx-config.conf"
echo "  3. 配置完成后运行：nginx -t && systemctl reload nginx"
echo ""
echo "备份文件位于服务器：/root/backups/"
echo ""
