#!/bin/bash

# 恢复备份脚本 - 20260303-234647
# 创建时间: 2026-03-04

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 路径定义
PROJECT_ROOT="/Users/gj/编程/ai助理new"
BACKUP_DIR="${PROJECT_ROOT}/bak/backup-20260303-234647"
BACKUP_EXTRACTED="${BACKUP_DIR}/ai-assistant-backup-20260303-234647"
CURRENT_BACKUP_DIR="${PROJECT_ROOT}/bak/backup-before-restore-$(date +%Y%m%d-%H%M%S)"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AI助理系统 - 备份恢复脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "恢复备份: 20260303-234647 (2026-03-03 23:46:58)"
echo "当前时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. 创建当前状态备份
echo -e "${YELLOW}步骤 1/5: 创建当前状态备份...${NC}"
mkdir -p "${CURRENT_BACKUP_DIR}"

# 备份当前Python代码
echo "  - 备份Python后端代码..."
cd "${PROJECT_ROOT}"
tar -czf "${CURRENT_BACKUP_DIR}/current_backend.tar.gz" \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='venv' \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='bak' \
    --exclude='uploads' \
    *.py *.sh *.json *.md 2>/dev/null || true

# 备份当前移动端项目
echo "  - 备份Flutter移动端项目..."
if [ -d "${PROJECT_ROOT}/ai-assistant-mobile" ]; then
    cd "${PROJECT_ROOT}/ai-assistant-mobile"
    tar -czf "${CURRENT_BACKUP_DIR}/current_mobile.tar.gz" \
        --exclude='build' \
        --exclude='.dart_tool' \
        --exclude='ios/Pods' \
        --exclude='android/.gradle' \
        --exclude='node_modules' \
        . 2>/dev/null || true
fi

echo -e "${GREEN}✓ 当前状态已备份到: ${CURRENT_BACKUP_DIR}${NC}"
echo ""

# 2. 恢复Python后端代码
echo -e "${YELLOW}步骤 2/5: 恢复Python后端代码...${NC}"
cd "${PROJECT_ROOT}"

# 复制Python文件
echo "  - 复制Python文件..."
cp -v "${BACKUP_EXTRACTED}/backend/"*.py . 2>/dev/null || true
cp -v "${BACKUP_EXTRACTED}/backend/"*.sh . 2>/dev/null || true

# 复制配置文件（保留现有的敏感配置）
echo "  - 复制配置文件..."
for config_file in ai_config.json mysql_config.json aliyun_email_config.json aliyun_sms_config.json; do
    if [ -f "${BACKUP_EXTRACTED}/backend/${config_file}" ]; then
        if [ -f "${PROJECT_ROOT}/${config_file}" ]; then
            echo "    ⚠️  ${config_file} 已存在，跳过（保留当前配置）"
        else
            cp -v "${BACKUP_EXTRACTED}/backend/${config_file}" .
        fi
    fi
done

echo -e "${GREEN}✓ Python后端代码恢复完成${NC}"
echo ""

# 3. 恢复Flutter移动端项目
echo -e "${YELLOW}步骤 3/5: 恢复Flutter移动端项目...${NC}"
if [ -d "${BACKUP_EXTRACTED}/projects/ai-assistant-mobile" ]; then
    echo "  - 复制Flutter项目文件..."

    # 复制lib目录
    if [ -d "${BACKUP_EXTRACTED}/projects/ai-assistant-mobile/lib" ]; then
        cp -r "${BACKUP_EXTRACTED}/projects/ai-assistant-mobile/lib" "${PROJECT_ROOT}/ai-assistant-mobile/"
        echo "    ✓ lib/ 目录已恢复"
    fi

    # 复制pubspec.yaml
    if [ -f "${BACKUP_EXTRACTED}/projects/ai-assistant-mobile/pubspec.yaml" ]; then
        cp "${BACKUP_EXTRACTED}/projects/ai-assistant-mobile/pubspec.yaml" "${PROJECT_ROOT}/ai-assistant-mobile/"
        echo "    ✓ pubspec.yaml 已恢复"
    fi

    # 复制iOS配置
    if [ -d "${BACKUP_EXTRACTED}/projects/ai-assistant-mobile/ios" ]; then
        cp -r "${BACKUP_EXTRACTED}/projects/ai-assistant-mobile/ios/Runner" "${PROJECT_ROOT}/ai-assistant-mobile/ios/" 2>/dev/null || true
        echo "    ✓ iOS配置已恢复"
    fi

    # 复制Android配置
    if [ -d "${BACKUP_EXTRACTED}/projects/ai-assistant-mobile/android" ]; then
        cp -r "${BACKUP_EXTRACTED}/projects/ai-assistant-mobile/android/app" "${PROJECT_ROOT}/ai-assistant-mobile/android/" 2>/dev/null || true
        echo "    ✓ Android配置已恢复"
    fi

    echo -e "${GREEN}✓ Flutter移动端项目恢复完成${NC}"
else
    echo -e "${YELLOW}⚠️  备份中未找到Flutter项目${NC}"
fi
echo ""

# 4. 恢复修改的依赖包
echo -e "${YELLOW}步骤 4/5: 恢复修改的依赖包...${NC}"
if [ -d "${BACKUP_EXTRACTED}/dependencies" ]; then
    echo "  - 检查reminders-2.0.2包..."
    if [ -d "${BACKUP_EXTRACTED}/dependencies/reminders-2.0.2" ]; then
        FLUTTER_CACHE_DIR="$HOME/.pub-cache/hosted/pub.dev/reminders-2.0.2"
        if [ -d "${FLUTTER_CACHE_DIR}" ]; then
            echo "    - 备份当前reminders包..."
            mv "${FLUTTER_CACHE_DIR}" "${FLUTTER_CACHE_DIR}.backup-$(date +%Y%m%d-%H%M%S)"
        fi
        echo "    - 恢复修改的reminders包..."
        mkdir -p "$(dirname ${FLUTTER_CACHE_DIR})"
        cp -r "${BACKUP_EXTRACTED}/dependencies/reminders-2.0.2" "${FLUTTER_CACHE_DIR}"
        echo -e "${GREEN}    ✓ reminders-2.0.2包已恢复${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  备份中未找到依赖包${NC}"
fi
echo ""

# 5. 数据库恢复提示
echo -e "${YELLOW}步骤 5/5: 数据库恢复${NC}"
echo ""
echo -e "${RED}⚠️  重要提示：数据库恢复需要手动执行${NC}"
echo ""
echo "数据库备份文件位置:"
echo "  ${BACKUP_DIR}/ai_assistant_db_backup_20260303-234647.sql"
echo ""
echo "恢复命令:"
echo -e "${GREEN}  mysql -u root -p ai_assistant < ${BACKUP_DIR}/ai_assistant_db_backup_20260303-234647.sql${NC}"
echo ""
echo "⚠️  注意："
echo "  1. 数据库恢复会覆盖当前所有数据"
echo "  2. 建议先备份当前数据库："
echo "     mysqldump -u root -p ai_assistant > current_db_backup.sql"
echo "  3. 确认无误后再执行恢复命令"
echo ""

# 完成
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}恢复完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "恢复内容:"
echo "  ✓ Python后端代码"
echo "  ✓ Flutter移动端项目"
echo "  ✓ 修改的依赖包"
echo "  ⚠️  数据库（需手动恢复）"
echo ""
echo "当前状态备份位置:"
echo "  ${CURRENT_BACKUP_DIR}"
echo ""
echo "后续步骤:"
echo "  1. 检查恢复的代码是否正确"
echo "  2. 如需恢复数据库，执行上述数据库恢复命令"
echo "  3. 重启服务: sudo supervisorctl restart ai-assistant"
echo "  4. Flutter项目需要重新构建: cd ai-assistant-mobile && flutter clean && flutter pub get"
echo ""
