#!/bin/bash
#############################################
# Git恢复脚本
# 用途：恢复到指定的提交或标签
# 用法：./git_restore.sh <commit-hash|tag>
#############################################

cd /var/www/ai-assistant

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检查是否提供了版本号
if [ -z "$1" ]; then
    echo -e "${RED}错误：请提供要恢复的版本${NC}"
    echo ""
    echo "用法: ./git_restore.sh <commit-hash|tag>"
    echo ""
    echo "示例:"
    echo "  ./git_restore.sh fe29c3e"
    echo "  ./git_restore.sh backup_20251214_104500"
    echo ""
    echo "查看可用版本："
    echo "  ./git_history.sh"
    exit 1
fi

TARGET="$1"

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  Git版本恢复${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# 检查目标是否存在
if ! git rev-parse "$TARGET" >/dev/null 2>&1; then
    echo -e "${RED}错误：找不到版本 '$TARGET'${NC}"
    echo ""
    echo "请使用 ./git_history.sh 查看可用版本"
    exit 1
fi

# 显示目标版本信息
echo -e "${YELLOW}目标版本信息：${NC}"
git log -1 --stat "$TARGET"
echo ""

# 确认操作
echo -e "${YELLOW}警告：此操作将恢复文件到指定版本！${NC}"
echo -e "${YELLOW}当前未保存的更改将会丢失！${NC}"
echo ""
read -p "确认要恢复吗？(yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${GREEN}操作已取消${NC}"
    exit 0
fi

# 先备份当前状态
echo ""
echo -e "${YELLOW}[1/4] 备份当前状态...${NC}"
BACKUP_TAG="backup_before_restore_$(date +%Y%m%d_%H%M%S)"
if [ -n "$(git status --porcelain)" ]; then
    git add .
    git commit -m "[自动备份] 恢复到 $TARGET 前的状态"
fi
git tag -a "$BACKUP_TAG" -m "恢复到 $TARGET 前的备份"
echo -e "${GREEN}✅ 当前状态已保存为标签: $BACKUP_TAG${NC}"

# 恢复文件
echo ""
echo -e "${YELLOW}[2/4] 恢复文件...${NC}"
git checkout "$TARGET" -- .

echo ""
echo -e "${YELLOW}[3/4] 提交恢复...${NC}"
git add .
git commit -m "[恢复] 恢复到版本 $TARGET"

# 重启服务
echo ""
echo -e "${YELLOW}[4/4] 重启服务...${NC}"
pkill -f 'python3 assistant_web.py'
sleep 2
nohup python3 assistant_web.py > server.log 2>&1 &
sleep 2

# 检查服务状态
if ps aux | grep 'python3 assistant_web.py' | grep -v grep >/dev/null; then
    echo -e "${GREEN}✅ 服务重启成功${NC}"
else
    echo -e "${RED}❌ 服务重启失败，请检查日志${NC}"
fi

echo ""
echo -e "${GREEN}✅ 恢复完成！${NC}"
echo ""
echo -e "${BLUE}如需撤销本次恢复，使用：${NC}"
echo -e "  ./git_restore.sh $BACKUP_TAG"
