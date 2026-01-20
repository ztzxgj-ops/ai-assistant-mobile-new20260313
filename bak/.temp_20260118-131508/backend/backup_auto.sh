#!/bin/bash
# ========================================
# AI助理系统 - 自动化完整备份（免密版）
# ========================================

set -e

SERVER="ai-server"  # 使用配置的别名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="ai-assistant-backup-${TIMESTAMP}"

echo "=========================================="
echo "AI助理系统 - 云服务器完全备份"
echo "=========================================="
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "目标服务器: 47.109.148.176"
echo "备份方式: SSH免密登录（自动化）"
echo ""

# ========================================
# 在服务器上执行备份
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[1/2] 在服务器上创建备份..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ssh ${SERVER} << 'ENDSSH'

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/ai-assistant-backup-${TIMESTAMP}"

echo "✓ 创建备份目录: ${BACKUP_DIR}"
mkdir -p ${BACKUP_DIR}/{code,database,nginx,supervisor}

# ========================================
# 1. 备份代码
# ========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "备份应用代码..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /var/www/ai-assistant

cp *.py ${BACKUP_DIR}/code/ 2>/dev/null && echo "  ✓ Python文件" || true
cp *.json ${BACKUP_DIR}/code/ 2>/dev/null && echo "  ✓ 配置文件" || true
cp *.sql ${BACKUP_DIR}/code/ 2>/dev/null && echo "  ✓ SQL脚本" || true
cp *.md ${BACKUP_DIR}/code/ 2>/dev/null && echo "  ✓ 文档" || true
cp *.sh ${BACKUP_DIR}/code/ 2>/dev/null && echo "  ✓ Shell脚本" || true
cp .gitignore ${BACKUP_DIR}/code/ 2>/dev/null && echo "  ✓ Git配置" || true

if [ -d "deploy" ]; then
    cp -r deploy ${BACKUP_DIR}/code/ && echo "  ✓ deploy目录"
fi

ls -lah ${BACKUP_DIR}/code/ > ${BACKUP_DIR}/code/FILE_LIST.txt

CODE_COUNT=$(ls -1 ${BACKUP_DIR}/code/*.py 2>/dev/null | wc -l | tr -d ' ')
echo "✅ 代码备份完成: ${CODE_COUNT} 个Python文件"

# ========================================
# 2. 备份数据库
# ========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "备份MySQL数据库..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mysqldump -u root -pgyq3160GYQ3160 --no-data ai_assistant > ${BACKUP_DIR}/database/schema.sql 2>/dev/null && echo "  ✓ 数据库结构"
mysqldump -u root -pgyq3160GYQ3160 ai_assistant > ${BACKUP_DIR}/database/full_backup.sql 2>/dev/null && echo "  ✓ 完整数据"

mysql -u root -pgyq3160GYQ3160 ai_assistant -e "
SELECT
    TABLE_NAME as 'Table',
    TABLE_ROWS as 'Rows',
    ROUND(DATA_LENGTH/1024/1024, 2) as 'Data_MB',
    ROUND(INDEX_LENGTH/1024/1024, 2) as 'Index_MB'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'ai_assistant'
ORDER BY TABLE_ROWS DESC;
" > ${BACKUP_DIR}/database/statistics.txt 2>/dev/null && echo "  ✓ 统计信息"

DB_SIZE=$(du -sh ${BACKUP_DIR}/database/ 2>/dev/null | cut -f1)
echo "✅ 数据库备份完成: ${DB_SIZE}"

# ========================================
# 3. 备份Nginx配置
# ========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "备份Nginx配置..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cp /etc/nginx/nginx.conf ${BACKUP_DIR}/nginx/ 2>/dev/null && echo "  ✓ nginx.conf" || echo "  ⚠ nginx.conf 未找到"
cp /etc/nginx/sites-available/default ${BACKUP_DIR}/nginx/default.conf 2>/dev/null && echo "  ✓ default.conf" || echo "  ⚠ default.conf 未找到"
grep -A 30 "location /ai/" /etc/nginx/sites-available/default > ${BACKUP_DIR}/nginx/ai-location.conf 2>/dev/null && echo "  ✓ AI助理配置段" || echo "  ⚠ AI配置未找到"

echo "✅ Nginx配置备份完成"

# ========================================
# 4. 备份Supervisor配置
# ========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "备份Supervisor配置..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cp /etc/supervisor/conf.d/ai-assistant.conf ${BACKUP_DIR}/supervisor/ 2>/dev/null && echo "  ✓ ai-assistant.conf" || echo "  ⚠ 配置文件未找到"
supervisorctl status > ${BACKUP_DIR}/supervisor/service_status.txt 2>/dev/null && echo "  ✓ 服务状态" || echo "  ⚠ Supervisor未运行"

echo "✅ Supervisor配置备份完成"

# ========================================
# 5. 生成说明文档
# ========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "生成备份文档..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cat > ${BACKUP_DIR}/README.md << 'EOF'
# AI助理系统 - 完全备份

## 备份时间
BACKUP_TIME

## 备份内容

### ✅ 已备份
- 所有Python源代码（*.py）
- 配置文件（*.json，包含密码和API密钥）
- SQL脚本、文档、Shell脚本
- 完整MySQL数据库（所有表和数据）
- Nginx配置文件
- Supervisor进程管理配置

### ❌ 未备份
- uploads/avatars/ - 用户头像
- uploads/images/ - 聊天图片
- 日志文件（*.log）
- Python缓存（__pycache__/）

## 恢复指南

### 恢复代码
```bash
scp -r code/* ai-server:/var/www/ai-assistant/
ssh ai-server "chown -R www-data:www-data /var/www/ai-assistant"
```

### 恢复数据库
```bash
scp database/full_backup.sql ai-server:/tmp/
ssh ai-server "mysql -u root -p ai_assistant < /tmp/full_backup.sql"
```

### 恢复配置
```bash
scp nginx/default.conf ai-server:/tmp/
scp supervisor/ai-assistant.conf ai-server:/etc/supervisor/conf.d/
ssh ai-server "supervisorctl reread && supervisorctl update"
```

## ⚠️ 安全警告
此备份包含敏感信息：
- MySQL数据库密码
- 通义千问API密钥
- 所有用户数据

请务必：
- 加密存储备份文件
- 不要上传到公共云盘
- 定期更新备份
EOF

sed -i "s/BACKUP_TIME/$(date '+%Y-%m-%d %H:%M:%S')/" ${BACKUP_DIR}/README.md 2>/dev/null || \
    sed -i "" "s/BACKUP_TIME/$(date '+%Y-%m-%d %H:%M:%S')/" ${BACKUP_DIR}/README.md

cat > ${BACKUP_DIR}/BACKUP_INFO.txt << EOF
========================================
AI助理系统备份信息
========================================
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
服务器: 47.109.148.176
备份目录: ${BACKUP_DIR}

统计信息:
- Python文件: $(ls -1 ${BACKUP_DIR}/code/*.py 2>/dev/null | wc -l | tr -d ' ') 个
- 配置文件: $(ls -1 ${BACKUP_DIR}/code/*.json 2>/dev/null | wc -l | tr -d ' ') 个
- 数据库: $(du -sh ${BACKUP_DIR}/database/ 2>/dev/null | cut -f1)
- 总大小: $(du -sh ${BACKUP_DIR} 2>/dev/null | cut -f1)

排除: uploads/, logs, cache
========================================
EOF

echo "  ✓ README.md"
echo "  ✓ BACKUP_INFO.txt"

# ========================================
# 6. 打包压缩
# ========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "打包压缩..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /tmp
tar -czf ${BACKUP_DIR}.tar.gz $(basename ${BACKUP_DIR})/ 2>/dev/null

echo ""
echo "=========================================="
echo "✅✅✅ 服务器端备份完成！"
echo "=========================================="
echo ""
echo "📦 备份文件: ${BACKUP_DIR}.tar.gz"
echo "📊 文件大小: $(du -sh ${BACKUP_DIR}.tar.gz | cut -f1)"
echo ""

# 输出文件名供下载使用
basename ${BACKUP_DIR}.tar.gz

ENDSSH

# ========================================
# 下载备份到本地
# ========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[2/2] 下载备份到本地..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 获取最新的备份文件
LATEST_BACKUP=$(ssh ${SERVER} "ls -t /tmp/ai-assistant-backup-*.tar.gz 2>/dev/null | head -1")

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ 无法找到备份文件"
    exit 1
fi

echo "正在下载: $(basename $LATEST_BACKUP)"
scp ${SERVER}:${LATEST_BACKUP} ./

if [ $? -eq 0 ]; then
    LOCAL_FILE=$(basename $LATEST_BACKUP)

    echo ""
    echo "=========================================="
    echo "🎉🎉🎉 备份任务全部完成！"
    echo "=========================================="
    echo ""
    echo "📦 本地文件: ${LOCAL_FILE}"
    echo "📊 文件大小: $(du -sh ${LOCAL_FILE} | cut -f1)"
    echo "📍 保存位置: $(pwd)/${LOCAL_FILE}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "快速操作:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📂 查看备份内容:"
    echo "   tar -tzf ${LOCAL_FILE} | head -20"
    echo ""
    echo "📖 解压并查看说明:"
    echo "   tar -xzf ${LOCAL_FILE}"
    echo "   cat $(basename $LOCAL_FILE .tar.gz)/README.md"
    echo ""
    echo "📋 查看备份信息:"
    echo "   tar -xzf ${LOCAL_FILE} $(basename $LOCAL_FILE .tar.gz)/BACKUP_INFO.txt -O"
    echo ""

    # 清理服务器临时文件
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧹 清理服务器临时文件..."
    ssh ${SERVER} "rm -rf /tmp/ai-assistant-backup-*"
    echo "✓ 服务器临时文件已清理"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "备份摘要"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 显示备份信息
    tar -xzf ${LOCAL_FILE} $(basename $LOCAL_FILE .tar.gz)/BACKUP_INFO.txt -O 2>/dev/null || true

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  安全提醒"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "1. 备份包含敏感信息（数据库密码、API密钥）"
    echo "2. 请将备份文件加密存储"
    echo "3. 不要上传到公共云盘"
    echo "4. 建议在对话结束后修改暴露的密码"
    echo ""
else
    echo ""
    echo "❌ 下载失败"
    echo "请手动下载:"
    echo "   scp ${SERVER}:${LATEST_BACKUP} ./"
fi
