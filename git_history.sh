#!/bin/bash
#############################################
# Git历史查看脚本
# 用途：查看提交历史和备份标签
# 用法：./git_history.sh [数量]
#############################################

cd /var/www/ai-assistant

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

LIMIT=${1:-10}

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  Git提交历史 (最近${LIMIT}条)${NC}"
echo -e "${BLUE}==========================================${NC}"
git log --oneline --graph --decorate -$LIMIT

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  所有备份标签${NC}"
echo -e "${BLUE}==========================================${NC}"
git tag | grep backup_ | tail -20 || echo "暂无备份标签"

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  当前状态${NC}"
echo -e "${BLUE}==========================================${NC}"
echo -e "当前分支: ${GREEN}$(git branch --show-current)${NC}"
echo -e "最后提交: ${GREEN}$(git log -1 --format='%h - %s (%ar)')${NC}"

if [ -n "$(git status --porcelain)" ]; then
    echo -e "状态: ${YELLOW}有未提交的更改${NC}"
    echo ""
    git status --short
else
    echo -e "状态: ${GREEN}工作目录干净${NC}"
fi
