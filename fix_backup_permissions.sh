#!/bin/bash
# ========================================
# 备份文件权限修复工具
# 用途：修复已有备份的文件权限，以及规范化tar.gz打包权限
# ========================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  备份文件权限修复工具${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查是否提供了备份文件路径
if [ -z "$1" ]; then
    echo -e "${YELLOW}用法: $0 <backup_tar_gz_file>${NC}"
    echo ""
    echo -e "示例:"
    echo "  $0 ai-assistant-backup-20260109-090311.tar.gz"
    echo "  $0 /Users/a1-6/Documents/GJ/编程/ai助理new/bak/backup-20260109-090311/ai-assistant-backup-20260109-090311.tar.gz"
    echo ""
    echo -e "${YELLOW}此工具会：${NC}"
    echo "  1. 提取备份文件"
    echo "  2. 修复所有文件的权限"
    echo "  3. 生成新的tar.gz文件（带 _fixed 后缀）"
    echo ""
    exit 0
fi

BACKUP_FILE="$1"

# 检查文件是否存在
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ 错误：文件不存在: $BACKUP_FILE${NC}"
    exit 1
fi

# 转换为绝对路径
BACKUP_FILE=$(cd "$(dirname "$BACKUP_FILE")" && pwd)/$(basename "$BACKUP_FILE")

# 检查是否为 tar.gz 文件
if [[ ! "$BACKUP_FILE" == *.tar.gz ]]; then
    echo -e "${RED}❌ 错误：文件不是 tar.gz 格式${NC}"
    exit 1
fi

# 获取文件大小
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo -e "${BLUE}备份文件信息${NC}"
echo "  文件: $BACKUP_FILE"
echo "  大小: $FILE_SIZE"
echo ""

# 创建工作目录
WORK_DIR="/tmp/backup_fix_$$"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo -e "${BLUE}步骤 1: 验证tar.gz文件完整性...${NC}"
if tar -tzf "$BACKUP_FILE" > /dev/null; then
    echo -e "${GREEN}✓${NC} 文件完整性验证通过"
else
    echo -e "${RED}❌ tar.gz文件损坏或不完整${NC}"
    rm -rf "$WORK_DIR"
    exit 1
fi

echo ""
echo -e "${BLUE}步骤 2: 解压备份文件...${NC}"
tar -xzf "$BACKUP_FILE"
EXTRACT_DIR=$(ls -d */ 2>/dev/null | head -1 | tr -d '/')
if [ -z "$EXTRACT_DIR" ]; then
    echo -e "${RED}❌ 无法确定解压目录${NC}"
    rm -rf "$WORK_DIR"
    exit 1
fi
echo -e "${GREEN}✓${NC} 解压完成: $EXTRACT_DIR"

echo ""
echo -e "${BLUE}步骤 3: 修复文件权限...${NC}"
echo "  设置目录权限: 755"
find "$EXTRACT_DIR" -type d -exec chmod 755 {} + 2>/dev/null || true
echo "  设置文件权限: 644"
find "$EXTRACT_DIR" -type f -exec chmod 644 {} + 2>/dev/null || true
echo -e "${GREEN}✓${NC} 权限修复完成"

echo ""
echo -e "${BLUE}步骤 4: 验证修复结果...${NC}"
# 统计权限
DIR_COUNT=$(find "$EXTRACT_DIR" -type d | wc -l)
FILE_COUNT=$(find "$EXTRACT_DIR" -type f | wc -l)
RESTRICTED_FILES=$(find "$EXTRACT_DIR" -type f ! -perm 644 | wc -l)

echo "  目录数: $DIR_COUNT"
echo "  文件数: $FILE_COUNT"
echo -e "  受限文件数: $([ "$RESTRICTED_FILES" -eq 0 ] && echo -e "${GREEN}0${NC}" || echo -e "${YELLOW}$RESTRICTED_FILES${NC}")"

echo ""
echo -e "${BLUE}步骤 5: 重新打包tar.gz文件...${NC}"

# 生成新的文件名
BACKUP_BASENAME=$(basename "$BACKUP_FILE" .tar.gz)
NEW_BACKUP_FILE="${BACKUP_BASENAME}_fixed.tar.gz"

# 使用tar重新打包，规范化权限
tar -czf "$NEW_BACKUP_FILE" "$EXTRACT_DIR" 2>/dev/null

if [ -f "$NEW_BACKUP_FILE" ]; then
    NEW_SIZE=$(du -h "$NEW_BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓${NC} 重新打包完成: $NEW_BACKUP_FILE"
    echo -e "${GREEN}✓${NC} 新文件大小: $NEW_SIZE"
else
    echo -e "${RED}❌ 重新打包失败${NC}"
    rm -rf "$WORK_DIR"
    exit 1
fi

echo ""
echo -e "${BLUE}步骤 6: 移动修复后的文件...${NC}"

# 获取原始文件的目录
ORIGINAL_DIR=$(dirname "$(cd "$(dirname "$BACKUP_FILE")" && pwd)"/$(basename "$BACKUP_FILE"))
ORIGINAL_DIR=$(cd "$(dirname "$BACKUP_FILE")" && pwd)

# 移动新文件到原始位置
cp "$NEW_BACKUP_FILE" "$ORIGINAL_DIR/$NEW_BACKUP_FILE"
if [ -f "$ORIGINAL_DIR/$NEW_BACKUP_FILE" ]; then
    echo -e "${GREEN}✓${NC} 文件已保存到: $ORIGINAL_DIR/$NEW_BACKUP_FILE"
else
    echo -e "${RED}❌ 无法保存文件${NC}"
    rm -rf "$WORK_DIR"
    exit 1
fi

echo ""
echo -e "${BLUE}步骤 7: 验证新的备份文件...${NC}"
# 测试新文件
TEST_DIR="/tmp/backup_test_$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
tar -xzf "$ORIGINAL_DIR/$NEW_BACKUP_FILE"

# 检查解压后的文件权限
SAMPLE_FILES=$(find . -type f | head -5)
SAMPLE_PERMS=$(ls -l $SAMPLE_FILES 2>/dev/null | awk '{print $1}' | sort | uniq)

echo -e "${GREEN}✓${NC} 新备份文件解压正常"
echo "  示例文件权限: $SAMPLE_PERMS"

# 清理测试目录
cd /
rm -rf "$TEST_DIR"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ 修复完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}修复结果:${NC}"
echo "  原始文件: $BACKUP_FILE"
echo "  修复后: $ORIGINAL_DIR/$NEW_BACKUP_FILE"
echo ""
echo -e "${YELLOW}💡 使用建议:${NC}"
echo "  1. 验证新文件无误后，可删除原始文件"
echo "  2. 建议解压验证: tar -xzf '$NEW_BACKUP_FILE'"
echo "  3. 确认所有文件可访问后再删除原始文件"
echo ""
echo -e "${YELLOW}下次备份:${NC}"
echo "  已更新的备份脚本会自动修复权限，无需手动处理"
echo ""

# 清理工作目录
rm -rf "$WORK_DIR"

# 播放提示音
afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || true
