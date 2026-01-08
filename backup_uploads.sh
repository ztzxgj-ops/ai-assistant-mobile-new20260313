#!/bin/bash
# ========================================
# AI助理系统 - 上传文件自动备份脚本
# 备份 uploads/ 目录（图片、头像、文件）
# ========================================

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 配置
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="uploads_backup_${TIMESTAMP}"
LOCAL_BAK_DIR="./bak"
SERVER="ai-server"
SERVER_BAK_DIR="/var/www/ai-assistant/backups"

echo ""
echo "=========================================="
echo -e "${BLUE}AI助理系统 - 上传文件备份${NC}"
echo "=========================================="
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ========================================
# 1. 检查uploads目录
# ========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[1/5] 检查上传文件目录${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ ! -d "uploads" ]; then
    echo -e "${RED}❌ uploads目录不存在${NC}"
    exit 1
fi

# 统计文件
AVATARS_COUNT=$(find uploads/avatars -type f 2>/dev/null | wc -l | tr -d ' ')
IMAGES_COUNT=$(find uploads/images -type f 2>/dev/null | wc -l | tr -d ' ')
FILES_COUNT=$(find uploads/files -type f 2>/dev/null | wc -l | tr -d ' ')

AVATARS_SIZE=$(du -sh uploads/avatars 2>/dev/null | cut -f1)
IMAGES_SIZE=$(du -sh uploads/images 2>/dev/null | cut -f1)
FILES_SIZE=$(du -sh uploads/files 2>/dev/null | cut -f1)
TOTAL_SIZE=$(du -sh uploads 2>/dev/null | cut -f1)

echo -e "${GREEN}✓${NC} uploads/avatars: ${AVATARS_COUNT} 个文件 (${AVATARS_SIZE})"
echo -e "${GREEN}✓${NC} uploads/images:  ${IMAGES_COUNT} 个文件 (${IMAGES_SIZE})"
echo -e "${GREEN}✓${NC} uploads/files:   ${FILES_COUNT} 个文件 (${FILES_SIZE})"
echo -e "${YELLOW}📊 总计: $((AVATARS_COUNT + IMAGES_COUNT + FILES_COUNT)) 个文件 (${TOTAL_SIZE})${NC}"

if [ "$((AVATARS_COUNT + IMAGES_COUNT + FILES_COUNT))" -eq 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  没有需要备份的文件${NC}"
    exit 0
fi

# ========================================
# 2. 创建本地备份目录
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[2/5] 创建本地备份目录${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

mkdir -p "${LOCAL_BAK_DIR}"
echo -e "${GREEN}✓${NC} 本地备份目录: ${LOCAL_BAK_DIR}"

# ========================================
# 3. 打包压缩
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[3/5] 打包压缩上传文件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

BACKUP_FILE="${LOCAL_BAK_DIR}/${BACKUP_NAME}.tar.gz"

echo "正在压缩..."
tar -czf "${BACKUP_FILE}" uploads/ 2>/dev/null

if [ -f "${BACKUP_FILE}" ]; then
    BACKUP_SIZE=$(du -sh "${BACKUP_FILE}" | cut -f1)
    echo -e "${GREEN}✅ 压缩完成${NC}"
    echo -e "${GREEN}📦 备份文件: ${BACKUP_FILE}${NC}"
    echo -e "${GREEN}📊 压缩大小: ${BACKUP_SIZE}${NC}"
else
    echo -e "${RED}❌ 压缩失败${NC}"
    exit 1
fi

# ========================================
# 4. 生成备份清单
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[4/5] 生成备份清单${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

MANIFEST_FILE="${LOCAL_BAK_DIR}/${BACKUP_NAME}_manifest.txt"

cat > "${MANIFEST_FILE}" << EOF
========================================
AI助理系统 - 上传文件备份清单
========================================
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份文件: ${BACKUP_NAME}.tar.gz
压缩大小: ${BACKUP_SIZE}

========================================
备份内容统计
========================================
头像文件 (avatars): ${AVATARS_COUNT} 个 (${AVATARS_SIZE})
聊天图片 (images):  ${IMAGES_COUNT} 个 (${IMAGES_SIZE})
上传文件 (files):   ${FILES_COUNT} 个 (${FILES_SIZE})
----------------------------------------
总计: $((AVATARS_COUNT + IMAGES_COUNT + FILES_COUNT)) 个文件 (${TOTAL_SIZE})
压缩后: ${BACKUP_SIZE}

========================================
文件列表
========================================
EOF

# 添加文件列表
echo "--- uploads/avatars ---" >> "${MANIFEST_FILE}"
find uploads/avatars -type f -exec ls -lh {} \; 2>/dev/null | awk '{print $9, "("$5")"}' >> "${MANIFEST_FILE}" || echo "无文件" >> "${MANIFEST_FILE}"

echo "" >> "${MANIFEST_FILE}"
echo "--- uploads/images ---" >> "${MANIFEST_FILE}"
find uploads/images -type f -exec ls -lh {} \; 2>/dev/null | awk '{print $9, "("$5")"}' >> "${MANIFEST_FILE}" || echo "无文件" >> "${MANIFEST_FILE}"

echo "" >> "${MANIFEST_FILE}"
echo "--- uploads/files ---" >> "${MANIFEST_FILE}"
find uploads/files -type f -exec ls -lh {} \; 2>/dev/null | awk '{print $9, "("$5")"}' >> "${MANIFEST_FILE}" || echo "无文件" >> "${MANIFEST_FILE}"

echo "" >> "${MANIFEST_FILE}"
echo "========================================" >> "${MANIFEST_FILE}"
echo "恢复方法" >> "${MANIFEST_FILE}"
echo "========================================" >> "${MANIFEST_FILE}"
echo "# 解压到当前目录" >> "${MANIFEST_FILE}"
echo "tar -xzf ${BACKUP_NAME}.tar.gz" >> "${MANIFEST_FILE}"
echo "" >> "${MANIFEST_FILE}"
echo "# 恢复到服务器" >> "${MANIFEST_FILE}"
echo "scp ${BACKUP_NAME}.tar.gz ai-server:/var/www/ai-assistant/" >> "${MANIFEST_FILE}"
echo "ssh ai-server \"cd /var/www/ai-assistant && tar -xzf ${BACKUP_NAME}.tar.gz\"" >> "${MANIFEST_FILE}"
echo "========================================" >> "${MANIFEST_FILE}"

echo -e "${GREEN}✓${NC} 备份清单: ${MANIFEST_FILE}"

# ========================================
# 5. 上传到云服务器
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[5/5] 上传备份到云服务器${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 在服务器上创建备份目录
ssh ${SERVER} "mkdir -p ${SERVER_BAK_DIR}" 2>/dev/null

echo "正在上传到云服务器..."
scp "${BACKUP_FILE}" ${SERVER}:${SERVER_BAK_DIR}/ 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 上传成功${NC}"
    echo -e "${GREEN}📍 服务器路径: ${SERVER}:${SERVER_BAK_DIR}/${BACKUP_NAME}.tar.gz${NC}"

    # 同时上传清单文件
    scp "${MANIFEST_FILE}" ${SERVER}:${SERVER_BAK_DIR}/ 2>/dev/null
    echo -e "${GREEN}✓${NC} 清单文件已上传"
else
    echo -e "${YELLOW}⚠️  上传到服务器失败，但本地备份已完成${NC}"
fi

# ========================================
# 完成
# ========================================
echo ""
echo "=========================================="
echo -e "${GREEN}🎉 备份任务完成！${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}本地备份:${NC}"
echo "  📦 ${BACKUP_FILE}"
echo "  📋 ${MANIFEST_FILE}"
echo ""
echo -e "${BLUE}云端备份:${NC}"
echo "  📍 ${SERVER}:${SERVER_BAK_DIR}/${BACKUP_NAME}.tar.gz"
echo ""
echo -e "${BLUE}快速操作:${NC}"
echo "  查看清单: cat ${MANIFEST_FILE}"
echo "  验证备份: tar -tzf ${BACKUP_FILE} | head -20"
echo "  解压恢复: tar -xzf ${BACKUP_FILE}"
echo ""

# ========================================
# 清理旧备份（可选）
# ========================================
OLD_BACKUPS_COUNT=$(ls -1 ${LOCAL_BAK_DIR}/uploads_backup_*.tar.gz 2>/dev/null | wc -l | tr -d ' ')

if [ "$OLD_BACKUPS_COUNT" -gt 5 ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⚠️  发现 ${OLD_BACKUPS_COUNT} 个历史备份${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "保留最近5个备份，删除较旧的备份？(y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        ls -t ${LOCAL_BAK_DIR}/uploads_backup_*.tar.gz | tail -n +6 | xargs rm -f
        echo -e "${GREEN}✓${NC} 已清理旧备份"
    fi
fi

echo ""
echo "=========================================="
echo "备份完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""
