#!/bin/bash
# ========================================
# AI助理系统 - 立即执行备份
# ========================================

set -e

# 服务器信息
SERVER="47.109.148.176"
USER="root"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="ai-assistant-backup-${TIMESTAMP}"

echo "=========================================="
echo "AI助理系统 - 云服务器全面备份"
echo "=========================================="
echo "开始时间: $(date)"
echo "目标服务器: ${SERVER}"
echo ""

# ========================================
# 在服务器上执行备份
# ========================================
echo "[步骤 1/7] 连接服务器并创建备份目录..."

sshpass -p 'gyq3160GYQ3160' ssh -o StrictHostKeyChecking=no ${USER}@${SERVER} << 'ENDSSH'

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/ai-assistant-backup-${TIMESTAMP}"
echo "创建备份目录: ${BACKUP_DIR}"
mkdir -p ${BACKUP_DIR}/{code,database,nginx,supervisor}

# ========================================
# 备份应用代码
# ========================================
echo ""
echo "[步骤 2/7] 备份应用代码..."
cd /var/www/ai-assistant

# Python文件
echo "  ✓ Python源代码"
cp *.py ${BACKUP_DIR}/code/ 2>/dev/null || true

# 配置文件
echo "  ✓ 配置文件"
cp *.json ${BACKUP_DIR}/code/ 2>/dev/null || true

# SQL文件
echo "  ✓ SQL脚本"
cp *.sql ${BACKUP_DIR}/code/ 2>/dev/null || true

# 文档
echo "  ✓ 文档文件"
cp *.md ${BACKUP_DIR}/code/ 2>/dev/null || true
cp CLAUDE.md ${BACKUP_DIR}/code/ 2>/dev/null || true

# Shell脚本
echo "  ✓ Shell脚本"
cp *.sh ${BACKUP_DIR}/code/ 2>/dev/null || true

# Git配置
echo "  ✓ Git配置"
cp .gitignore ${BACKUP_DIR}/code/ 2>/dev/null || true

# deploy目录
echo "  ✓ 部署文件"
if [ -d "deploy" ]; then
    cp -r deploy ${BACKUP_DIR}/code/
fi

# 创建文件清单
ls -lah ${BACKUP_DIR}/code/ > ${BACKUP_DIR}/code/FILE_LIST.txt
echo "代码文件备份完成"

# ========================================
# 备份数据库
# ========================================
echo ""
echo "[步骤 3/7] 备份MySQL数据库..."

# 数据库结构
echo "  ✓ 导出数据库结构"
mysqldump -u root -pgyq3160GYQ3160 --no-data ai_assistant > ${BACKUP_DIR}/database/schema.sql 2>/dev/null

# 完整数据
echo "  ✓ 导出完整数据"
mysqldump -u root -pgyq3160GYQ3160 ai_assistant > ${BACKUP_DIR}/database/full_backup.sql 2>/dev/null

# 数据统计
echo "  ✓ 导出统计信息"
mysql -u root -pgyq3160GYQ3160 ai_assistant -e "
SELECT
    TABLE_NAME as 'Table',
    TABLE_ROWS as 'Rows',
    ROUND(DATA_LENGTH/1024/1024, 2) as 'Data_MB',
    ROUND(INDEX_LENGTH/1024/1024, 2) as 'Index_MB'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'ai_assistant'
ORDER BY TABLE_ROWS DESC;
" > ${BACKUP_DIR}/database/statistics.txt 2>/dev/null

echo "数据库备份完成"

# ========================================
# 备份Nginx配置
# ========================================
echo ""
echo "[步骤 4/7] 备份Nginx配置..."

echo "  ✓ 主配置文件"
cp /etc/nginx/nginx.conf ${BACKUP_DIR}/nginx/nginx.conf 2>/dev/null || true

echo "  ✓ 站点配置"
cp /etc/nginx/sites-available/default ${BACKUP_DIR}/nginx/default.conf 2>/dev/null || true

echo "  ✓ AI助理配置段"
grep -A 30 "location /ai/" /etc/nginx/sites-available/default > ${BACKUP_DIR}/nginx/ai-location.conf 2>/dev/null || \
    echo "未找到AI助理配置" > ${BACKUP_DIR}/nginx/ai-location.conf

echo "Nginx配置备份完成"

# ========================================
# 备份Supervisor配置
# ========================================
echo ""
echo "[步骤 5/7] 备份Supervisor配置..."

echo "  ✓ 进程配置"
cp /etc/supervisor/conf.d/ai-assistant.conf ${BACKUP_DIR}/supervisor/ai-assistant.conf 2>/dev/null || \
    echo "未找到配置文件" > ${BACKUP_DIR}/supervisor/NOT_FOUND.txt

echo "  ✓ 服务状态"
supervisorctl status > ${BACKUP_DIR}/supervisor/service_status.txt 2>/dev/null || \
    echo "Supervisor未运行" > ${BACKUP_DIR}/supervisor/service_status.txt

echo "Supervisor配置备份完成"

# ========================================
# 创建备份说明
# ========================================
echo ""
echo "[步骤 6/7] 生成备份文档..."

cat > ${BACKUP_DIR}/README.md << 'EOF'
# AI助理系统 - 服务器完全备份

## 备份信息

- **备份时间**: BACKUP_TIME
- **服务器**: 47.109.148.176
- **备份内容**: 代码、配置、数据库（排除uploads/）

## 目录结构

```
├── code/              应用代码和配置
│   ├── *.py          Python源码
│   ├── *.json        配置文件（含密码）
│   ├── *.sql         SQL脚本
│   └── deploy/       部署文件
├── database/         数据库备份
│   ├── schema.sql    表结构
│   ├── full_backup.sql  完整数据
│   └── statistics.txt   统计信息
├── nginx/            Nginx配置
└── supervisor/       Supervisor配置
```

## 恢复方法

### 1. 恢复代码
```bash
scp -r code/* root@47.109.148.176:/var/www/ai-assistant/
ssh root@47.109.148.176 "chown -R www-data:www-data /var/www/ai-assistant"
```

### 2. 恢复数据库
```bash
scp database/full_backup.sql root@47.109.148.176:/tmp/
ssh root@47.109.148.176
mysql -u root -p ai_assistant < /tmp/full_backup.sql
```

### 3. 恢复配置
```bash
# Nginx（需手动合并）
scp nginx/default.conf root@47.109.148.176:/tmp/

# Supervisor
scp supervisor/ai-assistant.conf root@47.109.148.176:/etc/supervisor/conf.d/
ssh root@47.109.148.176 "supervisorctl reread && supervisorctl update"
```

## 注意事项

⚠️ **敏感信息**: 备份包含数据库密码和API密钥，请妥善保管
⚠️ **未备份**: uploads/目录（用户上传文件）需单独备份
⚠️ **恢复前**: 务必先备份当前服务器状态

EOF

sed -i "s/BACKUP_TIME/$(date '+%Y-%m-%d %H:%M:%S')/" ${BACKUP_DIR}/README.md 2>/dev/null || \
    sed -i "" "s/BACKUP_TIME/$(date '+%Y-%m-%d %H:%M:%S')/" ${BACKUP_DIR}/README.md

# 创建备份信息文件
cat > ${BACKUP_DIR}/BACKUP_INFO.txt << EOF
====================================
AI助理系统备份信息
====================================

备份时间: $(date '+%Y-%m-%d %H:%M:%S')
服务器: 47.109.148.176
备份位置: ${BACKUP_DIR}

备份内容统计:
- Python文件: $(ls -1 ${BACKUP_DIR}/code/*.py 2>/dev/null | wc -l) 个
- 配置文件: $(ls -1 ${BACKUP_DIR}/code/*.json 2>/dev/null | wc -l) 个
- 数据库大小: $(du -sh ${BACKUP_DIR}/database/ 2>/dev/null | cut -f1)
- 总大小: $(du -sh ${BACKUP_DIR} 2>/dev/null | cut -f1)

排除内容:
- uploads/ 目录（用户上传文件）
- __pycache__/ 缓存
- *.log 日志
- *.pyc 编译文件

====================================
EOF

echo "备份文档生成完成"

# ========================================
# 打包压缩
# ========================================
echo ""
echo "[步骤 7/7] 打包压缩..."

cd /tmp
BACKUP_DIRNAME=$(basename ${BACKUP_DIR})
tar -czf ${BACKUP_DIRNAME}.tar.gz ${BACKUP_DIRNAME}/ 2>/dev/null

echo ""
echo "=========================================="
echo "✓ 服务器端备份完成！"
echo "=========================================="
echo "备份文件: /tmp/${BACKUP_DIRNAME}.tar.gz"
echo "文件大小: $(du -sh /tmp/${BACKUP_DIRNAME}.tar.gz 2>/dev/null | cut -f1)"
echo ""

# 输出备份文件名供后续使用
echo "${BACKUP_DIRNAME}.tar.gz"

ENDSSH

# 保存服务器返回的备份文件名
BACKUP_FILE=$(sshpass -p 'gyq3160GYQ3160' ssh ${USER}@${SERVER} "ls -t /tmp/ai-assistant-backup-*.tar.gz 2>/dev/null | head -1")

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ 无法获取备份文件名"
    exit 1
fi

# ========================================
# 下载备份到本地
# ========================================
echo ""
echo "=========================================="
echo "下载备份到本地..."
echo "=========================================="

LOCAL_BACKUP="ai-assistant-backup-${TIMESTAMP}.tar.gz"

echo "正在下载: $(basename ${BACKUP_FILE})"
sshpass -p 'gyq3160GYQ3160' scp ${USER}@${SERVER}:${BACKUP_FILE} ./${LOCAL_BACKUP}

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓✓✓ 备份任务全部完成！"
    echo "=========================================="
    echo ""
    echo "📦 本地备份文件: ${LOCAL_BACKUP}"
    echo "📊 文件大小: $(du -sh ${LOCAL_BACKUP} | cut -f1)"
    echo "📍 保存位置: $(pwd)/${LOCAL_BACKUP}"
    echo ""
    echo "📖 查看备份内容:"
    echo "   tar -tzf ${LOCAL_BACKUP}"
    echo ""
    echo "📂 解压备份:"
    echo "   tar -xzf ${LOCAL_BACKUP}"
    echo ""

    # 清理服务器临时文件
    echo "🧹 清理服务器临时文件..."
    sshpass -p 'gyq3160GYQ3160' ssh ${USER}@${SERVER} "rm -rf /tmp/ai-assistant-backup-*"
    echo "✓ 服务器清理完成"

    echo ""
    echo "⚠️  安全提醒:"
    echo "   • 备份包含数据库密码和API密钥"
    echo "   • 请妥善保管，建议加密存储"
    echo "   • 建议修改对话中暴露的密码"
    echo ""
else
    echo "❌ 下载失败，请手动下载:"
    echo "   scp ${USER}@${SERVER}:${BACKUP_FILE} ./"
fi
