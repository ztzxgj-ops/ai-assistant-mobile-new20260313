#!/bin/bash
#############################################
# AI助理系统一键部署脚本
# 适用于：Ubuntu 18.04/20.04/22.04, Debian 10/11
# 作者：AI Assistant
# 日期：2025-12-10
#############################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
APP_NAME="ai-assistant"
INSTALL_DIR="/var/www/ai-assistant"
NGINX_CONF="/etc/nginx/sites-available/default"
SUPERVISOR_CONF="/etc/supervisor/conf.d/ai-assistant.conf"
PYTHON_BIN="/usr/bin/python3"
DB_NAME="ai_assistant"
DB_USER="ai_assistant"
DB_PASS="ai_assistant_2024"  # 生产环境请修改为强密码

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查是否以root运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用root权限运行此脚本: sudo bash deploy.sh"
        exit 1
    fi
}

# 检查系统类型
check_system() {
    log_step "检查系统环境..."
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log_info "系统: $NAME $VERSION"
    else
        log_error "无法识别系统类型"
        exit 1
    fi
}

# 安装依赖
install_dependencies() {
    log_step "安装系统依赖..."

    apt update
    apt install -y python3 python3-pip nginx supervisor mysql-client curl wget

    log_info "Python版本: $(python3 --version)"
    log_info "Nginx版本: $(nginx -v 2>&1)"
}

# 安装Python包
install_python_packages() {
    log_step "安装Python依赖包..."

    pip3 install --upgrade pip
    pip3 install pymysql

    log_info "Python包安装完成"
}

# 创建目录
create_directories() {
    log_step "创建应用目录..."

    mkdir -p $INSTALL_DIR
    mkdir -p $INSTALL_DIR/uploads/avatars
    mkdir -p $INSTALL_DIR/uploads/images
    mkdir -p /var/log

    log_info "目录创建完成"
}

# 配置数据库
setup_database() {
    log_step "配置MySQL数据库..."

    # 检查MySQL是否运行
    if ! systemctl is-active --quiet mysql && ! systemctl is-active --quiet mariadb; then
        log_warn "MySQL/MariaDB服务未运行，跳过数据库配置"
        log_warn "请手动运行: mysql -u root -p < database_schema.sql"
        return
    fi

    log_info "请输入MySQL root密码："
    read -s MYSQL_ROOT_PASS

    # 创建数据库和用户
    mysql -u root -p"$MYSQL_ROOT_PASS" <<EOF
CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

    # 导入数据库结构
    if [ -f "$INSTALL_DIR/database_schema.sql" ]; then
        mysql -u root -p"$MYSQL_ROOT_PASS" $DB_NAME < "$INSTALL_DIR/database_schema.sql"
        log_info "数据库导入完成"
    else
        log_warn "未找到database_schema.sql，请手动导入"
    fi
}

# 配置文件权限
set_permissions() {
    log_step "设置文件权限..."

    chown -R www-data:www-data $INSTALL_DIR
    chmod -R 755 $INSTALL_DIR
    chmod -R 775 $INSTALL_DIR/uploads
    chmod 600 $INSTALL_DIR/mysql_config.json
    chmod 600 $INSTALL_DIR/ai_config.json

    log_info "权限设置完成"
}

# 配置Nginx
setup_nginx() {
    log_step "配置Nginx..."

    # 备份原配置
    if [ -f "$NGINX_CONF" ]; then
        cp $NGINX_CONF ${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)
        log_info "原配置已备份"
    fi

    # 检查是否存在部署配置
    if [ -f "$INSTALL_DIR/deploy/nginx-config.conf" ]; then
        log_warn "检测到新的Nginx配置文件"
        log_warn "请手动合并配置: $INSTALL_DIR/deploy/nginx-config.conf"
        log_warn "到: $NGINX_CONF"
        echo ""
        echo "或者直接复制（会覆盖原配置）："
        echo "cp $INSTALL_DIR/deploy/nginx-config.conf $NGINX_CONF"
    else
        log_warn "未找到Nginx配置模板，请手动配置"
    fi

    # 测试配置
    if nginx -t 2>/dev/null; then
        systemctl reload nginx
        log_info "Nginx配置成功"
    else
        log_error "Nginx配置测试失败，请检查配置文件"
    fi
}

# 配置Supervisor
setup_supervisor() {
    log_step "配置Supervisor..."

    if [ -f "$INSTALL_DIR/deploy/supervisor-config.conf" ]; then
        cp $INSTALL_DIR/deploy/supervisor-config.conf $SUPERVISOR_CONF

        # 更新配置
        supervisorctl reread
        supervisorctl update
        supervisorctl start $APP_NAME

        log_info "Supervisor配置完成"
    else
        log_error "未找到Supervisor配置文件"
    fi
}

# 检查服务状态
check_services() {
    log_step "检查服务状态..."

    echo ""
    echo "=== Nginx状态 ==="
    systemctl status nginx --no-pager -l | head -10

    echo ""
    echo "=== Supervisor状态 ==="
    supervisorctl status $APP_NAME

    echo ""
    echo "=== Python进程 ==="
    ps aux | grep assistant_web.py | grep -v grep
}

# 显示访问信息
show_access_info() {
    echo ""
    echo "=========================================="
    log_info "部署完成！"
    echo "=========================================="
    echo ""
    echo "访问地址："
    echo "  - 智能鱼缸系统: http://$(hostname -I | awk '{print $1}')/"
    echo "  - AI助理系统:   http://$(hostname -I | awk '{print $1}')/ai/"
    echo ""
    echo "常用命令："
    echo "  - 查看日志: tail -f /var/log/ai-assistant.log"
    echo "  - 重启服务: supervisorctl restart $APP_NAME"
    echo "  - 查看状态: supervisorctl status $APP_NAME"
    echo "  - 停止服务: supervisorctl stop $APP_NAME"
    echo ""
    echo "配置文件："
    echo "  - 应用目录: $INSTALL_DIR"
    echo "  - Nginx配置: $NGINX_CONF"
    echo "  - Supervisor: $SUPERVISOR_CONF"
    echo ""
    log_warn "首次部署请检查："
    echo "  1. MySQL配置 (mysql_config.json)"
    echo "  2. AI配置 (ai_config.json)"
    echo "  3. Nginx配置是否正确合并"
    echo "=========================================="
}

# 主函数
main() {
    echo ""
    echo "=========================================="
    echo "   AI助理系统 - 一键部署脚本"
    echo "=========================================="
    echo ""

    check_root
    check_system

    log_warn "即将开始部署，是否继续？(y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 0
    fi

    install_dependencies
    install_python_packages
    create_directories
    setup_database
    set_permissions
    setup_nginx
    setup_supervisor
    check_services
    show_access_info
}

# 执行主函数
main
