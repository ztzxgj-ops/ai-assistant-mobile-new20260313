#!/bin/bash
#############################################
# Git安全更新脚本
# 用途：修改文件前自动备份和提交
# 用法：./git_safe_update.sh "修改前的说明"
#############################################

cd /var/www/ai-assistant

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TAG_NAME="backup_$TIMESTAMP"
COMMIT_MSG="${1:-修改前的自动备份}"

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  Git安全更新 - 自动备份系统${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}[1/5] 检测到未提交的更改${NC}"
    git status --short
    
    echo ""
    echo -e "${YELLOW}[2/5] 添加所有更改到暂存区...${NC}"
    git add .
    
    echo ""
    echo -e "${YELLOW}[3/5] 提交更改...${NC}"
    git commit -m "[$(date +%Y-%m-%d\ %H:%M)] $COMMIT_MSG"
    
    echo ""
    echo -e "${YELLOW}[4/5] 创建备份标签: $TAG_NAME${NC}"
    git tag -a "$TAG_NAME" -m "自动备份: $COMMIT_MSG"
    
    echo ""
    echo -e "${YELLOW}[5/5] 提交信息${NC}"
    git log -1 --stat
    
    echo ""
    echo -e "${GREEN}✅ 备份完成！标签：$TAG_NAME${NC}"
    echo ""
    echo -e "${GREEN}如需恢复到此版本，使用：${NC}"
    echo -e "  git checkout $TAG_NAME"
    echo ""
else
    echo -e "${GREEN}✅ 工作目录是干净的，无需备份${NC}"
fi

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  最近的5次提交:${NC}"
echo -e "${BLUE}==========================================${NC}"
git log --oneline -5

echo ""
echo -e "${BLUE}  所有备份标签:${NC}"
echo -e "${BLUE}==========================================${NC}"
git tag | grep backup_ | tail -10
