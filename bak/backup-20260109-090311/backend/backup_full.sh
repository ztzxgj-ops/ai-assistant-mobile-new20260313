#!/bin/bash
# ========================================
# AI助理系统 - 完整自动备份脚本
# 包含：代码 + 数据库 + 配置 + 上传文件
# 保存到：本地bak目录 + 云服务器
# ========================================

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="ai_assistant_full_backup_${TIMESTAMP}"
LOCAL_BAK_DIR="./bak"
SERVER="ai-server"
SERVER_BAK_DIR="/var/www/ai-assistant/backups"

clear
echo ""
echo "=========================================="
echo -e "${CYAN}   AI助理系统 - 完整自动备份${NC}"
echo "=========================================="
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "备份名称: ${BACKUP_NAME}"
echo ""

# ========================================
# 1. 准备备份目录
# ========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[1/6] 准备备份目录${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

mkdir -p "${LOCAL_BAK_DIR}"
TEMP_DIR="${LOCAL_BAK_DIR}/.temp_${TIMESTAMP}"
mkdir -p "${TEMP_DIR}"/{code,database,nginx,supervisor,uploads,logs}

echo -e "${GREEN}✓${NC} 临时目录: ${TEMP_DIR}"
echo -e "${GREEN}✓${NC} 本地备份目录: ${LOCAL_BAK_DIR}"

# ========================================
# 2. 备份本地代码和配置
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[2/6] 备份本地代码和配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Python文件
cp *.py "${TEMP_DIR}/code/" 2>/dev/null && echo -e "${GREEN}✓${NC} Python源文件" || true

# 配置文件
cp *.json "${TEMP_DIR}/code/" 2>/dev/null && echo -e "${GREEN}✓${NC} 配置文件" || true

# SQL脚本
cp *.sql "${TEMP_DIR}/code/" 2>/dev/null && echo -e "${GREEN}✓${NC} SQL脚本" || true

# 文档
cp *.md "${TEMP_DIR}/code/" 2>/dev/null && echo -e "${GREEN}✓${NC} 文档文件" || true

# Shell脚本
cp *.sh "${TEMP_DIR}/code/" 2>/dev/null && echo -e "${GREEN}✓${NC} Shell脚本" || true

# Git配置
cp .gitignore "${TEMP_DIR}/code/" 2>/dev/null && echo -e "${GREEN}✓${NC} Git配置" || true

# deploy目录
if [ -d "deploy" ]; then
    cp -r deploy "${TEMP_DIR}/code/" && echo -e "${GREEN}✓${NC} deploy目录"
fi

CODE_COUNT=$(ls -1 ${TEMP_DIR}/code/*.py 2>/dev/null | wc -l | tr -d ' ')
echo -e "${YELLOW}📊 代码备份: ${CODE_COUNT} 个Python文件${NC}"

# ========================================
# 3. 备份上传文件
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[3/6] 备份上传文件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -d "uploads" ]; then
    # 备份avatars
    if [ -d "uploads/avatars" ]; then
        cp -r uploads/avatars "${TEMP_DIR}/uploads/" 2>/dev/null
        AVATARS_COUNT=$(find uploads/avatars -type f 2>/dev/null | wc -l | tr -d ' ')
        AVATARS_SIZE=$(du -sh uploads/avatars 2>/dev/null | cut -f1)
        echo -e "${GREEN}✓${NC} avatars: ${AVATARS_COUNT} 个文件 (${AVATARS_SIZE})"
    fi

    # 备份images
    if [ -d "uploads/images" ]; then
        cp -r uploads/images "${TEMP_DIR}/uploads/" 2>/dev/null
        IMAGES_COUNT=$(find uploads/images -type f 2>/dev/null | wc -l | tr -d ' ')
        IMAGES_SIZE=$(du -sh uploads/images 2>/dev/null | cut -f1)
        echo -e "${GREEN}✓${NC} images:  ${IMAGES_COUNT} 个文件 (${IMAGES_SIZE})"
    fi

    # 备份files
    if [ -d "uploads/files" ]; then
        cp -r uploads/files "${TEMP_DIR}/uploads/" 2>/dev/null
        FILES_COUNT=$(find uploads/files -type f 2>/dev/null | wc -l | tr -d ' ')
        FILES_SIZE=$(du -sh uploads/files 2>/dev/null | cut -f1)
        echo -e "${GREEN}✓${NC} files:   ${FILES_COUNT} 个文件 (${FILES_SIZE})"
    fi

    TOTAL_UPLOADS_SIZE=$(du -sh uploads 2>/dev/null | cut -f1)
    echo -e "${YELLOW}📊 上传文件备份: ${TOTAL_UPLOADS_SIZE}${NC}"
else
    echo -e "${YELLOW}⚠️  uploads目录不存在${NC}"
fi

# ========================================
# 4. 从服务器备份数据库
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[4/6] 从服务器备份数据库${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

ssh ${SERVER} "mysqldump -u root -pgyq3160GYQ3160 --no-data ai_assistant 2>/dev/null" > "${TEMP_DIR}/database/schema.sql" && echo -e "${GREEN}✓${NC} 数据库结构" || echo -e "${YELLOW}⚠️  数据库结构备份失败${NC}"

ssh ${SERVER} "mysqldump -u root -pgyq3160GYQ3160 ai_assistant 2>/dev/null" > "${TEMP_DIR}/database/full_backup.sql" && echo -e "${GREEN}✓${NC} 完整数据" || echo -e "${YELLOW}⚠️  数据库备份失败${NC}"

ssh ${SERVER} "mysql -u root -pgyq3160GYQ3160 ai_assistant -e \"
SELECT
    TABLE_NAME as 'Table',
    TABLE_ROWS as 'Rows',
    ROUND(DATA_LENGTH/1024/1024, 2) as 'Data_MB',
    ROUND(INDEX_LENGTH/1024/1024, 2) as 'Index_MB'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'ai_assistant'
ORDER BY TABLE_ROWS DESC;
\" 2>/dev/null" > "${TEMP_DIR}/database/statistics.txt" && echo -e "${GREEN}✓${NC} 统计信息" || true

DB_SIZE=$(du -sh ${TEMP_DIR}/database/ 2>/dev/null | cut -f1)
echo -e "${YELLOW}📊 数据库备份: ${DB_SIZE}${NC}"

# ========================================
# 5. 从服务器备份配置文件
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[5/6] 从服务器备份配置文件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Nginx配置
scp ${SERVER}:/etc/nginx/nginx.conf "${TEMP_DIR}/nginx/" 2>/dev/null && echo -e "${GREEN}✓${NC} nginx.conf" || echo -e "${YELLOW}⚠️  nginx.conf未找到${NC}"

scp ${SERVER}:/etc/nginx/sites-available/default "${TEMP_DIR}/nginx/default.conf" 2>/dev/null && echo -e "${GREEN}✓${NC} default.conf" || true

# Supervisor配置
scp ${SERVER}:/etc/supervisor/conf.d/ai-assistant.conf "${TEMP_DIR}/supervisor/" 2>/dev/null && echo -e "${GREEN}✓${NC} supervisor配置" || echo -e "${YELLOW}⚠️  supervisor配置未找到${NC}"

ssh ${SERVER} "supervisorctl status 2>/dev/null" > "${TEMP_DIR}/supervisor/service_status.txt" && echo -e "${GREEN}✓${NC} 服务状态" || true

# 日志文件（最近1000行）
ssh ${SERVER} "tail -1000 /var/log/ai-assistant.log 2>/dev/null" > "${TEMP_DIR}/logs/ai-assistant.log" && echo -e "${GREEN}✓${NC} 应用日志" || true

# ========================================
# 6. 生成备份文档和打包
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[6/6] 生成备份文档和打包${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 生成README
cat > "${TEMP_DIR}/README.md" << EOF
# AI助理系统 - 完整备份

## 备份信息
- **备份时间**: $(date '+%Y-%m-%d %H:%M:%S')
- **备份名称**: ${BACKUP_NAME}
- **服务器**: 47.109.148.176 (ai-server)

## 备份内容

### ✅ 本地文件
- Python源代码 (${CODE_COUNT} 个文件)
- 配置文件 (*.json)
- SQL脚本、文档、Shell脚本
- deploy部署脚本

### ✅ 上传文件
- uploads/avatars (用户头像): ${AVATARS_COUNT:-0} 个文件
- uploads/images (聊天图片): ${IMAGES_COUNT:-0} 个文件
- uploads/files (上传文件): ${FILES_COUNT:-0} 个文件
- 总大小: ${TOTAL_UPLOADS_SIZE:-0}

### ✅ 服务器数据
- MySQL数据库 (完整备份)
- Nginx配置文件
- Supervisor进程管理配置
- 应用日志 (最近1000行)

## 备份统计
\`\`\`
代码文件: ${CODE_COUNT} 个
上传文件: $((${AVATARS_COUNT:-0} + ${IMAGES_COUNT:-0} + ${FILES_COUNT:-0})) 个
数据库: ${DB_SIZE}
总大小: $(du -sh ${TEMP_DIR} 2>/dev/null | cut -f1)
\`\`\`

## 恢复指南

### 1. 恢复代码
\`\`\`bash
# 解压备份
tar -xzf ${BACKUP_NAME}.tar.gz

# 上传到服务器
scp -r code/* ai-server:/var/www/ai-assistant/

# 设置权限
ssh ai-server "chown -R www-data:www-data /var/www/ai-assistant"
\`\`\`

### 2. 恢复上传文件
\`\`\`bash
# 上传文件目录
scp -r uploads/* ai-server:/var/www/ai-assistant/uploads/

# 设置权限
ssh ai-server "chown -R www-data:www-data /var/www/ai-assistant/uploads"
ssh ai-server "chmod -R 775 /var/www/ai-assistant/uploads"
\`\`\`

### 3. 恢复数据库
\`\`\`bash
# 上传数据库备份
scp database/full_backup.sql ai-server:/tmp/

# 恢复数据库
ssh ai-server "mysql -u root -p ai_assistant < /tmp/full_backup.sql"
\`\`\`

### 4. 恢复配置
\`\`\`bash
# Nginx配置
scp nginx/default.conf ai-server:/tmp/
ssh ai-server "sudo cp /tmp/default.conf /etc/nginx/sites-available/default"
ssh ai-server "sudo nginx -t && sudo systemctl reload nginx"

# Supervisor配置
scp supervisor/ai-assistant.conf ai-server:/etc/supervisor/conf.d/
ssh ai-server "sudo supervisorctl reread && sudo supervisorctl update"
\`\`\`

### 5. 重启服务
\`\`\`bash
ssh ai-server "sudo supervisorctl restart ai-assistant"
\`\`\`

## ⚠️ 安全警告

此备份包含敏感信息：
- MySQL root密码
- 通义千问API密钥
- 所有用户数据（消息、文件、头像）

请务必：
- ✅ 加密存储备份文件
- ✅ 定期更新备份
- ❌ 不要上传到公共云盘
- ❌ 不要分享给未授权人员

## 备份文件结构
\`\`\`
${BACKUP_NAME}/
├── code/           # 代码和配置
├── database/       # 数据库备份
├── nginx/          # Nginx配置
├── supervisor/     # Supervisor配置
├── uploads/        # 用户上传文件
├── logs/           # 应用日志
└── README.md       # 本文件
\`\`\`

---
Generated by AI Assistant Backup System
EOF

echo -e "${GREEN}✓${NC} README.md"

# 生成备份信息
cat > "${TEMP_DIR}/BACKUP_INFO.txt" << EOF
========================================
AI助理系统 - 备份信息
========================================
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份名称: ${BACKUP_NAME}
服务器: 47.109.148.176

========================================
备份内容统计
========================================
代码文件: ${CODE_COUNT} 个Python文件
上传文件: $((${AVATARS_COUNT:-0} + ${IMAGES_COUNT:-0} + ${FILES_COUNT:-0})) 个
- avatars: ${AVATARS_COUNT:-0} 个 (${AVATARS_SIZE:-0})
- images:  ${IMAGES_COUNT:-0} 个 (${IMAGES_SIZE:-0})
- files:   ${FILES_COUNT:-0} 个 (${FILES_SIZE:-0})

数据库: ${DB_SIZE}
总大小: $(du -sh ${TEMP_DIR} 2>/dev/null | cut -f1)

========================================
文件清单
========================================
EOF

find "${TEMP_DIR}" -type f | sed "s|${TEMP_DIR}/||" >> "${TEMP_DIR}/BACKUP_INFO.txt"

echo -e "${GREEN}✓${NC} BACKUP_INFO.txt"

# 打包压缩
echo ""
echo "正在压缩打包..."
cd "${LOCAL_BAK_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" ".temp_${TIMESTAMP}" 2>/dev/null

if [ -f "${BACKUP_NAME}.tar.gz" ]; then
    BACKUP_SIZE=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)
    echo -e "${GREEN}✅ 压缩完成${NC}"
    echo -e "${GREEN}📦 备份文件: ${LOCAL_BAK_DIR}/${BACKUP_NAME}.tar.gz${NC}"
    echo -e "${GREEN}📊 文件大小: ${BACKUP_SIZE}${NC}"

    # 清理临时目录
    rm -rf ".temp_${TIMESTAMP}"
    echo -e "${GREEN}✓${NC} 临时文件已清理"
else
    echo -e "${RED}❌ 压缩失败${NC}"
    exit 1
fi

cd - > /dev/null

# ========================================
# 上传到云服务器
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}上传备份到云服务器${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 创建服务器备份目录
ssh ${SERVER} "mkdir -p ${SERVER_BAK_DIR}" 2>/dev/null

echo "正在上传..."
scp "${LOCAL_BAK_DIR}/${BACKUP_NAME}.tar.gz" ${SERVER}:${SERVER_BAK_DIR}/ 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 上传成功${NC}"
    echo -e "${GREEN}📍 服务器路径: ${SERVER}:${SERVER_BAK_DIR}/${BACKUP_NAME}.tar.gz${NC}"
else
    echo -e "${YELLOW}⚠️  上传失败，但本地备份已完成${NC}"
fi

# ========================================
# 完成
# ========================================
echo ""
echo "=========================================="
echo -e "${GREEN}🎉🎉🎉 备份任务全部完成！${NC}"
echo "=========================================="
echo ""
echo -e "${CYAN}📦 本地备份${NC}"
echo "  文件: ${LOCAL_BAK_DIR}/${BACKUP_NAME}.tar.gz"
echo "  大小: ${BACKUP_SIZE}"
echo ""
echo -e "${CYAN}☁️  云端备份${NC}"
echo "  位置: ${SERVER}:${SERVER_BAK_DIR}/"
echo "  文件: ${BACKUP_NAME}.tar.gz"
echo ""
echo -e "${CYAN}📊 备份统计${NC}"
echo "  代码: ${CODE_COUNT} 个文件"
echo "  上传: $((${AVATARS_COUNT:-0} + ${IMAGES_COUNT:-0} + ${FILES_COUNT:-0})) 个文件"
echo "  数据库: ${DB_SIZE}"
echo ""
echo -e "${CYAN}🔧 快速操作${NC}"
echo "  查看内容: tar -tzf ${LOCAL_BAK_DIR}/${BACKUP_NAME}.tar.gz | head -30"
echo "  查看说明: tar -xzf ${LOCAL_BAK_DIR}/${BACKUP_NAME}.tar.gz .temp_*/README.md -O"
echo "  解压恢复: tar -xzf ${LOCAL_BAK_DIR}/${BACKUP_NAME}.tar.gz"
echo ""
echo "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# ========================================
# 清理旧备份提醒
# ========================================
OLD_BACKUPS=$(ls -1 ${LOCAL_BAK_DIR}/ai_assistant_full_backup_*.tar.gz 2>/dev/null | wc -l | tr -d ' ')
if [ "$OLD_BACKUPS" -gt 3 ]; then
    echo -e "${YELLOW}⚠️  本地有 ${OLD_BACKUPS} 个历史备份，建议定期清理${NC}"
    echo ""
fi
