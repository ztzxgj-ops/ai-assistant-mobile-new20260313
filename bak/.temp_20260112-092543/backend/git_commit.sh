#!/bin/bash
#############################################
# Git快速提交脚本
# 用途：快速提交代码修改
# 用法：./git_commit.sh "提交说明"
#############################################

cd /var/www/ai-assistant

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查是否提供了提交信息
if [ -z "$1" ]; then
    echo -e "${RED}错误：请提供提交信息${NC}"
    echo "用法: ./git_commit.sh '提交说明'"
    exit 1
fi

COMMIT_MSG="$1"

echo -e "${YELLOW}[1/4] 检查文件状态...${NC}"
git status --short

echo ""
echo -e "${YELLOW}[2/4] 添加文件到暂存区...${NC}"
git add .

echo ""
echo -e "${YELLOW}[3/4] 提交更改...${NC}"
git commit -m "[$(date +%Y-%m-%d\ %H:%M)] $COMMIT_MSG"

echo ""
echo -e "${YELLOW}[4/4] 查看提交历史...${NC}"
git log --oneline -5

echo ""
echo -e "${GREEN}✅ 提交完成！${NC}"
