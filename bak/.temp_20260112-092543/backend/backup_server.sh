#!/bin/bash
# AI助理系统自动备份脚本
# 用途：备份云服务器的代码、配置和数据库到本地

# 配置
SERVER_IP="47.109.148.176"
SERVER_PASSWORD="gyq3160GYQ3160"
SERVER_USER="root"
SERVER_PATH="/var/www/ai-assistant"
LOCAL_BAK_DIR="/Users/gj/编程/ai助理new/bak"
DB_NAME="ai_assistant"
DB_USER="ai_assistant"
DB_PASSWORD="ai_assistant_2024"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 时间戳
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DATE_CN=$(date '+%Y年%m月%d日 %H:%M:%S')

# ✨ 创建以日期时间命名的备份子目录
BACKUP_SUBDIR="backup-${TIMESTAMP}"
CURRENT_BACKUP_DIR="${LOCAL_BAK_DIR}/${BACKUP_SUBDIR}"

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

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    if ! command -v sshpass &> /dev/null; then
        log_error "未安装 sshpass，请先安装: brew install sshpass"
        exit 1
    fi

    log_info "依赖检查通过 ✓"
}

# 创建本地备份目录
create_local_dir() {
    log_info "创建本地备份目录..."
    mkdir -p "$LOCAL_BAK_DIR"

    # ✨ 创建本次备份的子目录
    mkdir -p "$CURRENT_BACKUP_DIR"
    log_info "本次备份目录: $CURRENT_BACKUP_DIR ✓"
}

# 备份代码和配置文件
backup_code() {
    log_info "开始备份代码和配置文件..."

    # 在服务器上创建备份（不包含bak目录）
    BACKUP_NAME="ai-assistant-backup-${TIMESTAMP}.tar.gz"

    sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP \
        "cd $SERVER_PATH && tar --exclude='uploads' --exclude='bak' --exclude='__pycache__' --exclude='*.pyc' \
        -czf /tmp/$BACKUP_NAME *.py *.json *.md deploy/ 2>/dev/null"

    if [ $? -eq 0 ]; then
        log_info "服务器备份创建成功 ✓"
    else
        log_error "服务器备份创建失败"
        return 1
    fi

    # ✨ 下载到本次备份的子目录（添加重试机制和大小验证）
    log_info "下载备份到本地..."

    # 获取服务器文件大小
    SERVER_SIZE=$(sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP \
        "stat -c%s /tmp/$BACKUP_NAME 2>/dev/null || stat -f%z /tmp/$BACKUP_NAME 2>/dev/null")

    # 尝试下载，最多重试3次
    MAX_RETRIES=3
    RETRY_COUNT=0
    DOWNLOAD_SUCCESS=false

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        sshpass -p "$SERVER_PASSWORD" scp -o StrictHostKeyChecking=no \
            $SERVER_USER@$SERVER_IP:/tmp/$BACKUP_NAME \
            "$CURRENT_BACKUP_DIR/$BACKUP_NAME"

        if [ $? -eq 0 ]; then
            # 验证文件大小
            LOCAL_SIZE=$(stat -f%z "$CURRENT_BACKUP_DIR/$BACKUP_NAME" 2>/dev/null || stat -c%s "$CURRENT_BACKUP_DIR/$BACKUP_NAME" 2>/dev/null)

            if [ "$LOCAL_SIZE" = "$SERVER_SIZE" ]; then
                log_info "代码备份完成 ✓ ($BACKUP_NAME, 大小: $(numfmt --to=iec $LOCAL_SIZE 2>/dev/null || echo $LOCAL_SIZE))"
                echo "$BACKUP_NAME" > /tmp/backup_code_name.txt
                DOWNLOAD_SUCCESS=true
                break
            else
                log_warn "文件大小不匹配 (本地: $LOCAL_SIZE, 服务器: $SERVER_SIZE)，重试中..."
                RETRY_COUNT=$((RETRY_COUNT + 1))
                sleep 2
            fi
        else
            log_warn "下载失败，重试中... (尝试 $((RETRY_COUNT + 1))/$MAX_RETRIES)"
            RETRY_COUNT=$((RETRY_COUNT + 1))
            sleep 2
        fi
    done

    if [ "$DOWNLOAD_SUCCESS" = true ]; then
        return 0
    else
        log_error "下载备份失败（已重试 $MAX_RETRIES 次）"
        return 1
    fi
}

# 备份数据库
backup_database() {
    log_info "开始备份数据库..."

    DB_BACKUP_NAME="ai_assistant_db_backup_${TIMESTAMP}.sql"

    # 在服务器上导出数据库
    sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP \
        "mysqldump -u $DB_USER -p'$DB_PASSWORD' $DB_NAME --single-transaction --quick --lock-tables=false > /tmp/$DB_BACKUP_NAME"

    if [ $? -eq 0 ]; then
        log_info "数据库导出成功 ✓"
    else
        log_error "数据库导出失败"
        return 1
    fi

    # ✨ 下载到本次备份的子目录（添加重试机制和大小验证）
    log_info "下载数据库备份到本地..."

    # 获取服务器文件大小
    SERVER_SIZE=$(sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP \
        "stat -c%s /tmp/$DB_BACKUP_NAME 2>/dev/null || stat -f%z /tmp/$DB_BACKUP_NAME 2>/dev/null")

    # 尝试下载，最多重试3次
    MAX_RETRIES=3
    RETRY_COUNT=0
    DOWNLOAD_SUCCESS=false

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        sshpass -p "$SERVER_PASSWORD" scp -o StrictHostKeyChecking=no \
            $SERVER_USER@$SERVER_IP:/tmp/$DB_BACKUP_NAME \
            "$CURRENT_BACKUP_DIR/$DB_BACKUP_NAME"

        if [ $? -eq 0 ]; then
            # 验证文件大小
            LOCAL_SIZE=$(stat -f%z "$CURRENT_BACKUP_DIR/$DB_BACKUP_NAME" 2>/dev/null || stat -c%s "$CURRENT_BACKUP_DIR/$DB_BACKUP_NAME" 2>/dev/null)

            if [ "$LOCAL_SIZE" = "$SERVER_SIZE" ]; then
                log_info "数据库备份完成 ✓ ($DB_BACKUP_NAME, 大小: $(numfmt --to=iec $LOCAL_SIZE 2>/dev/null || echo $LOCAL_SIZE))"
                echo "$DB_BACKUP_NAME" > /tmp/backup_db_name.txt
                DOWNLOAD_SUCCESS=true
                break
            else
                log_warn "文件大小不匹配 (本地: $LOCAL_SIZE, 服务器: $SERVER_SIZE)，重试中..."
                RETRY_COUNT=$((RETRY_COUNT + 1))
                sleep 2
            fi
        else
            log_warn "下载失败，重试中... (尝试 $((RETRY_COUNT + 1))/$MAX_RETRIES)"
            RETRY_COUNT=$((RETRY_COUNT + 1))
            sleep 2
        fi
    done

    if [ "$DOWNLOAD_SUCCESS" = true ]; then
        return 0
    else
        log_error "下载数据库备份失败（已重试 $MAX_RETRIES 次）"
        return 1
    fi
}

# 创建备份说明
create_readme() {
    log_info "创建备份说明..."

    BACKUP_CODE_NAME=$(cat /tmp/backup_code_name.txt 2>/dev/null)
    BACKUP_DB_NAME=$(cat /tmp/backup_db_name.txt 2>/dev/null)

    # ✨ 备份说明保存到子目录中
    README_FILE="$CURRENT_BACKUP_DIR/备份说明.txt"

    cat > "$README_FILE" << EOF
AI助理系统备份说明
==================

备份时间: $DATE_CN
备份目录: $BACKUP_SUBDIR
备份类型: 自动备份

📦 备份内容
-----------
1. 所有Python源代码 (*.py)
2. 配置文件 (*.json)
3. 文档文件 (*.md)
4. 部署脚本 (deploy/)
5. MySQL数据库完整备份

❌ 排除内容
-----------
- uploads/ 目录 (图片和文件上传)
- bak/ 目录 (历史备份)
- __pycache__/ 目录
- *.pyc 编译文件

📍 备份位置
-----------
云端服务器 ($SERVER_IP):
  - /tmp/$BACKUP_CODE_NAME
  - /tmp/$BACKUP_DB_NAME

本地备份 ($CURRENT_BACKUP_DIR):
  - $BACKUP_CODE_NAME
  - $BACKUP_DB_NAME
  - 备份说明.txt

📊 文件大小
-----------
EOF

    # 添加文件大小信息
    if [ -f "$CURRENT_BACKUP_DIR/$BACKUP_CODE_NAME" ]; then
        SIZE=$(du -h "$CURRENT_BACKUP_DIR/$BACKUP_CODE_NAME" | awk '{print $1}')
        echo "代码备份: $SIZE" >> "$README_FILE"
    fi

    if [ -f "$CURRENT_BACKUP_DIR/$BACKUP_DB_NAME" ]; then
        SIZE=$(du -h "$CURRENT_BACKUP_DIR/$BACKUP_DB_NAME" | awk '{print $1}')
        echo "数据库备份: $SIZE" >> "$README_FILE"
    fi

    cat >> "$README_FILE" << 'EOF'

🔄 恢复方法
-----------
EOF

    cat >> "$README_FILE" << EOF
# 1. 恢复代码文件
tar -xzf $BACKUP_CODE_NAME -C $SERVER_PATH/

# 2. 恢复数据库
mysql -u $DB_USER -p'$DB_PASSWORD' $DB_NAME < $BACKUP_DB_NAME

# 3. 重启服务
sudo supervisorctl restart ai-assistant

📝 备份脚本
-----------
使用自动备份脚本: backup_server.sh
下次备份建议: $(date -v+1d '+%Y年%m月%d日')

生成时间: $DATE_CN
EOF

    log_info "备份说明创建完成 ✓"

    # 清理临时文件
    rm -f /tmp/backup_code_name.txt /tmp/backup_db_name.txt
}

# 清理旧备份（保留最近10个备份目录）
cleanup_old_backups() {
    log_info "清理旧备份..."

    cd "$LOCAL_BAK_DIR" || return

    # ✨ 保留最近10个备份目录（backup-YYYYMMDD-HHMMSS）
    BACKUP_DIR_COUNT=$(ls -dt backup-* 2>/dev/null | wc -l)
    if [ "$BACKUP_DIR_COUNT" -gt 10 ]; then
        log_info "删除旧的备份目录（保留最近10个）..."
        ls -dt backup-* | tail -n +11 | xargs rm -rf
    fi

    log_info "旧备份清理完成 ✓"
}

# 显示备份摘要
show_summary() {
    echo ""
    echo "======================================"
    log_info "备份完成摘要"
    echo "======================================"
    echo "备份时间: $DATE_CN"
    echo "备份目录: $CURRENT_BACKUP_DIR"
    echo ""
    echo "备份文件列表:"
    ls -lh "$CURRENT_BACKUP_DIR" | tail -n +2 | awk '{printf "  %s  %s\n", $5, $9}'
    echo "======================================"
    echo ""
    echo "💡 提示：备份已保存到 $BACKUP_SUBDIR 目录"
    echo ""

    # 播放完成提示音
    afplay /System/Library/Sounds/Glass.aiff 2>/dev/null &
}

# 主函数
main() {
    echo "======================================"
    echo "  AI助理系统自动备份工具"
    echo "======================================"
    echo "开始时间: $DATE_CN"
    echo ""

    check_dependencies
    create_local_dir

    if backup_code && backup_database; then
        create_readme
        cleanup_old_backups
        show_summary
        exit 0
    else
        log_error "备份过程中出现错误"
        exit 1
    fi
}

# 执行主函数
main
