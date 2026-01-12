#!/bin/bash
# ========================================
# AI助理系统 - 标准系统备份脚本
# 包含：Python后端 + iOS/Flutter + Electron + 修改的依赖 + 数据库 + 配置
# 排除：uploads用户上传文件（头像、图片、文件）
# 保存到：本地bak目录 + 云服务器
# ========================================

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# 配置
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOCAL_BAK_DIR="./bak"
BACKUP_DIR_NAME="backup-${TIMESTAMP}"
BACKUP_DIR="${LOCAL_BAK_DIR}/${BACKUP_DIR_NAME}"

# 云服务器配置（使用sshpass直接连接）
SERVER_IP="47.109.148.176"
SERVER_USER="root"
SERVER_PASSWORD="gyq3160GYQ3160"
SERVER_PATH="/var/www/ai-assistant"
SERVER_BAK_DIR="/var/www/ai-assistant/backups"

clear
echo ""
echo "=========================================="
echo -e "${CYAN}   AI助理系统 - 标准系统备份${NC}"
echo "=========================================="
echo "备份时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "备份目录: ${BACKUP_DIR_NAME}"
echo -e "${YELLOW}⚠️  注意: 此备份不包含 uploads/ 用户上传文件${NC}"
echo ""

# ========================================
# 1. 准备备份目录结构
# ========================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[1/7] 准备备份目录结构${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

mkdir -p "${LOCAL_BAK_DIR}"
mkdir -p "${BACKUP_DIR}"
TEMP_DIR="${LOCAL_BAK_DIR}/.temp_${TIMESTAMP}"
mkdir -p "${TEMP_DIR}"/{backend,projects,dependencies,database,config,docs}

echo -e "${GREEN}✓${NC} 备份目录: ${BACKUP_DIR}"
echo -e "${GREEN}✓${NC} 临时目录: ${TEMP_DIR}"

# ========================================
# 2. 备份 Python 后端系统
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[2/7] 备份 Python 后端系统${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Python源文件
cp *.py "${TEMP_DIR}/backend/" 2>/dev/null && echo -e "${GREEN}✓${NC} Python源文件" || true

# 配置文件 (敏感!)
cp *.json "${TEMP_DIR}/backend/" 2>/dev/null && echo -e "${GREEN}✓${NC} 配置文件 (mysql_config.json, ai_config.json)" || true

# SQL脚本
cp *.sql "${TEMP_DIR}/backend/" 2>/dev/null && echo -e "${GREEN}✓${NC} SQL脚本" || true

# 文档
cp *.md "${TEMP_DIR}/docs/" 2>/dev/null && echo -e "${GREEN}✓${NC} 文档文件" || true

# Shell脚本
cp *.sh "${TEMP_DIR}/backend/" 2>/dev/null && echo -e "${GREEN}✓${NC} Shell脚本" || true

# Git配置
cp .gitignore "${TEMP_DIR}/backend/" 2>/dev/null && echo -e "${GREEN}✓${NC} Git配置" || true

# deploy目录
if [ -d "deploy" ]; then
    cp -r deploy "${TEMP_DIR}/backend/" && echo -e "${GREEN}✓${NC} deploy目录"
fi

CODE_COUNT=$(ls -1 ${TEMP_DIR}/backend/*.py 2>/dev/null | wc -l | tr -d ' ')
echo -e "${YELLOW}📊 Python后端: ${CODE_COUNT} 个文件${NC}"

# ========================================
# 3. 备份 iOS/Flutter 移动项目
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[3/7] 备份 iOS/Flutter 移动项目${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -d "ai-assistant-mobile" ]; then
    echo "正在备份 Flutter 项目 (排除 build/, .dart_tool/, ios/Pods/)..."

    # 使用 rsync 排除大型构建目录
    rsync -av \
        --exclude='build' \
        --exclude='.dart_tool' \
        --exclude='ios/Pods' \
        --exclude='ios/.symlinks' \
        --exclude='android/.gradle' \
        --exclude='macos/Pods' \
        ai-assistant-mobile/ "${TEMP_DIR}/projects/ai-assistant-mobile/" 2>/dev/null

    FLUTTER_SIZE=$(du -sh "${TEMP_DIR}/projects/ai-assistant-mobile" 2>/dev/null | cut -f1)
    echo -e "${GREEN}✓${NC} Flutter项目: ${FLUTTER_SIZE}"

    # 统计关键文件
    DART_FILES=$(find "${TEMP_DIR}/projects/ai-assistant-mobile" -name "*.dart" 2>/dev/null | wc -l | tr -d ' ')
    echo -e "${GREEN}✓${NC} Dart源文件: ${DART_FILES} 个"
else
    echo -e "${YELLOW}⚠️  ai-assistant-mobile 目录不存在${NC}"
fi

# ========================================
# 4. 备份 Electron 桌面项目 (排除 node_modules)
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[4/7] 备份 Electron 桌面项目${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -d "ai-assistant-electron" ]; then
    echo "正在备份 Electron 项目 (排除 node_modules/, dist/)..."

    # 使用 rsync 排除 node_modules 和构建目录
    rsync -av \
        --exclude='node_modules' \
        --exclude='dist' \
        --exclude='out' \
        --exclude='.webpack' \
        ai-assistant-electron/ "${TEMP_DIR}/projects/ai-assistant-electron/" 2>/dev/null

    ELECTRON_SIZE=$(du -sh "${TEMP_DIR}/projects/ai-assistant-electron" 2>/dev/null | cut -f1)
    echo -e "${GREEN}✓${NC} Electron项目: ${ELECTRON_SIZE}"
    echo -e "${GREEN}✓${NC} package.json (恢复时运行 npm install)"
else
    echo -e "${YELLOW}⚠️  ai-assistant-electron 目录不存在${NC}"
fi

# ========================================
# 5. 备份修改的第三方依赖 (关键!)
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[5/7] 备份修改的第三方依赖 (极关键!)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

REMINDERS_PATH=~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2

if [ -d "${REMINDERS_PATH}" ]; then
    echo "正在备份修改的 reminders-2.0.2 包..."
    cp -r "${REMINDERS_PATH}" "${TEMP_DIR}/dependencies/reminders-2.0.2-modified" 2>/dev/null

    REMINDERS_SIZE=$(du -sh "${TEMP_DIR}/dependencies/reminders-2.0.2-modified" 2>/dev/null | cut -f1)
    echo -e "${GREEN}✓${NC} reminders-2.0.2: ${REMINDERS_SIZE}"

    # 生成修改说明文档
    cat > "${TEMP_DIR}/dependencies/MODIFICATIONS.md" << 'EOF'
# 第三方依赖修改记录

## reminders-2.0.2 包修改

**修改日期**: 2025-12-27
**修改原因**: 支持循环提醒功能 (yearly/monthly/weekly/daily)

### 修改文件详情:

#### 1. lib/reminder.dart
**路径**: `~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2/lib/reminder.dart`

**修改内容**:
- Line 11: 添加 `String? recurrence;` 字段
- Line 21: 构造函数添加 `this.recurrence` 参数
- Line 30: fromJson 添加 `recurrence = json['recurrence']`
- Line 59-60: toJson 添加条件包含 recurrence

**代码示例**:
```dart
String? recurrence;  // 新增：循环类型 (yearly/monthly/weekly/daily)

Reminder(
    {required this.list,
    this.id,
    required this.title,
    this.dueDate,
    this.priority = 0,
    this.isCompleted = false,
    this.notes,
    this.recurrence});  // 新增

// toJson() 方法
if (recurrence != null) {
  json['recurrence'] = recurrence;
}
```

#### 2. ios/Classes/Reminders.swift
**路径**: `~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2/ios/Classes/Reminders.swift`

**修改内容**:
- Line 118: 添加 `case "daily"` 支持每日循环

**代码示例**:
```swift
case "daily":
    recurrenceRule = EKRecurrenceRule(
        recurrenceWith: .daily,
        interval: 1,
        end: nil
    )
```

### 恢复方法:

#### 快速恢复 (推荐):
```bash
# 从备份中恢复
cp -r dependencies/reminders-2.0.2-modified \
  ~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2

# 验证修改
cat ~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2/lib/reminder.dart | grep recurrence

# 重新构建 Flutter 项目
cd /Users/a1-6/Documents/GJ/编程/ai助理new/ai-assistant-mobile
flutter clean
flutter pub get
cd ios && pod install
```

#### 手动恢复 (如果自动恢复失败):
1. 打开 `lib/reminder.dart` 文件
2. 添加 `String? recurrence;` 字段
3. 修改 toJson() 和 fromJson() 方法
4. 打开 `ios/Classes/Reminders.swift` 文件
5. 添加 daily case 到 switch 语句

### ⚠️ 重要警告:

1. **不要运行 `flutter pub upgrade reminders`** - 会覆盖修改
2. **重装 Flutter 后必须先恢复此包** - 否则循环提醒功能失效
3. **备份此文件夹是最高优先级** - 丢失需要手动重新修改

### 验证检查:

```bash
# 检查 recurrence 字段是否存在
grep -n "String? recurrence" ~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2/lib/reminder.dart

# 检查 daily case 是否存在
grep -n "case \"daily\"" ~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2/ios/Classes/Reminders.swift

# 如果两个命令都有输出，说明修改完整
```

---
**备份日期**: $(date '+%Y-%m-%d %H:%M:%S')
**备份脚本**: backup_complete_system.sh
EOF

    echo -e "${GREEN}✓${NC} 修改说明文档: MODIFICATIONS.md"
    echo -e "${MAGENTA}⚠️  关键依赖已备份，丢失后需手动重新修改!${NC}"
else
    echo -e "${RED}❌ reminders-2.0.2 包未找到: ${REMINDERS_PATH}${NC}"
    echo -e "${YELLOW}⚠️  这是关键依赖，建议检查路径是否正确${NC}"
fi

# ========================================
# 注意：标准备份不包含 uploads/ 用户上传文件
# 如需备份用户上传文件，请使用"完整备份"选项
# ========================================

# ========================================
# 6. 从服务器备份数据库和配置
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[6/7] 从服务器备份数据库和配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 数据库备份
echo "正在备份 MySQL 数据库..."
sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "mysqldump -u root -pgyq3160GYQ3160 --no-data ai_assistant 2>/dev/null" > "${TEMP_DIR}/database/schema.sql" && echo -e "${GREEN}✓${NC} 数据库结构" || echo -e "${YELLOW}⚠️  数据库结构备份失败${NC}"

sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "mysqldump -u root -pgyq3160GYQ3160 ai_assistant 2>/dev/null" > "${TEMP_DIR}/database/full_backup.sql" && echo -e "${GREEN}✓${NC} 完整数据" || echo -e "${YELLOW}⚠️  数据库备份失败${NC}"

# 数据库统计
sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "mysql -u root -pgyq3160GYQ3160 ai_assistant -e \"
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
echo -e "${YELLOW}📊 数据库: ${DB_SIZE}${NC}"

# 配置文件备份
echo ""
echo "正在备份配置文件..."
sshpass -p "${SERVER_PASSWORD}" scp -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP}:/etc/nginx/sites-available/default "${TEMP_DIR}/config/nginx_default.conf" 2>/dev/null && echo -e "${GREEN}✓${NC} Nginx配置" || echo -e "${YELLOW}⚠️  Nginx配置未找到${NC}"

sshpass -p "${SERVER_PASSWORD}" scp -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP}:/etc/supervisor/conf.d/ai-assistant.conf "${TEMP_DIR}/config/supervisor.conf" 2>/dev/null && echo -e "${GREEN}✓${NC} Supervisor配置" || echo -e "${YELLOW}⚠️  Supervisor配置未找到${NC}"

sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "supervisorctl status 2>/dev/null" > "${TEMP_DIR}/config/service_status.txt" && echo -e "${GREEN}✓${NC} 服务状态" || true

# ========================================
# 8. 生成完整恢复指南和打包
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[7/7] 生成恢复指南和打包${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 生成完整恢复指南
cat > "${TEMP_DIR}/RECOVERY_GUIDE.md" << 'EOFRECOVERY'
# AI助理系统 - 完整恢复指南

## 📋 备份信息

- **备份时间**: $(date '+%Y-%m-%d %H:%M:%S')
- **备份名称**: ${BACKUP_NAME}
- **服务器**: 47.109.148.176 (ai-server)

---

## 🔄 完整系统恢复顺序

### 前提条件检查

```bash
# 1. 检查备份文件完整性
gzip -t bak/${BACKUP_NAME}.tar.gz

# 2. 检查可用磁盘空间
df -h .

# 3. 检查开发环境
flutter --version
node --version
python3 --version
```

---

### 步骤 1: 解压备份包

```bash
# 下载云端备份 (如需要)
scp ai-server:/var/www/ai-assistant/backups/${BACKUP_NAME}.tar.gz ~/

# 解压到当前目录
cd ~
tar -xzf ${BACKUP_NAME}.tar.gz
cd .temp_*
```

---

### 步骤 2: 恢复 Python 后端

```bash
# 恢复到本地开发目录
mkdir -p ~/Documents/GJ/编程/ai助理new
cp -r backend/* ~/Documents/GJ/编程/ai助理new/

# 恢复文档
cp -r docs/* ~/Documents/GJ/编程/ai助理new/

# 恢复到服务器 (如需要)
cd backend/
scp *.py ai-server:/var/www/ai-assistant/
scp *.json ai-server:/var/www/ai-assistant/
ssh ai-server "chown -R www-data:www-data /var/www/ai-assistant"
```

---

### 步骤 3: ⚠️ 恢复修改的依赖 (极关键!)

**必须在恢复 Flutter 项目之前执行!**

```bash
# 创建 .pub-cache 目录 (如不存在)
mkdir -p ~/.pub-cache/hosted/pub.flutter-io.cn/

# 恢复修改的 reminders 包
cp -r dependencies/reminders-2.0.2-modified \
  ~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2

# 验证恢复
cat ~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2/lib/reminder.dart | grep recurrence

# 如果看到 "String? recurrence;" 输出，说明恢复成功
```

**验证检查**:
```bash
# 检查 recurrence 字段
grep -n "String? recurrence" \
  ~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2/lib/reminder.dart

# 检查 daily case
grep -n "case \"daily\"" \
  ~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2/ios/Classes/Reminders.swift

# 两个命令都有输出才算成功
```

---

### 步骤 4: 恢复 iOS/Flutter 项目

```bash
# 恢复项目源代码
cp -r projects/ai-assistant-mobile ~/Documents/GJ/编程/ai助理new/

# 进入项目目录
cd ~/Documents/GJ/编程/ai助理new/ai-assistant-mobile

# 清理并安装依赖
flutter clean
flutter pub get

# 安装 CocoaPods 依赖
cd ios
pod install

# 验证
cd ..
flutter doctor
```

**常见问题**:
- 如果 `pod install` 失败，运行 `pod repo update`
- 如果构建失败提示 recurrence 字段错误，说明步骤3未正确执行

---

### 步骤 5: 恢复 Electron 项目

```bash
# 恢复项目源代码
cp -r projects/ai-assistant-electron ~/Documents/GJ/编程/ai助理new/

# 进入项目目录
cd ~/Documents/GJ/编程/ai助理new/ai-assistant-electron

# 安装 npm 依赖
npm install

# 验证
npm run build
```

---

### 步骤 6: 恢复数据库

```bash
# 上传数据库备份到服务器
scp database/full_backup.sql ai-server:/tmp/

# 恢复数据库
ssh ai-server "mysql -u root -pgyq3160GYQ3160 ai_assistant < /tmp/full_backup.sql"

# 验证
ssh ai-server "mysql -u root -pgyq3160GYQ3160 -e 'USE ai_assistant; SHOW TABLES;'"

# 清理临时文件
ssh ai-server "rm /tmp/full_backup.sql"
```

---

### 步骤 7: 恢复上传文件

```bash
# 本地恢复
cp -r uploads/* ~/Documents/GJ/编程/ai助理new/uploads/

# 服务器恢复
scp -r uploads/* ai-server:/var/www/ai-assistant/uploads/

# 设置权限
ssh ai-server "chown -R www-data:www-data /var/www/ai-assistant/uploads"
ssh ai-server "chmod -R 775 /var/www/ai-assistant/uploads"
```

---

### 步骤 8: 恢复服务器配置

```bash
# Nginx 配置
scp config/nginx_default.conf ai-server:/tmp/
ssh ai-server "sudo cp /tmp/nginx_default.conf /etc/nginx/sites-available/default"
ssh ai-server "sudo nginx -t"
ssh ai-server "sudo systemctl reload nginx"

# Supervisor 配置
scp config/supervisor.conf ai-server:/etc/supervisor/conf.d/ai-assistant.conf
ssh ai-server "sudo supervisorctl reread"
ssh ai-server "sudo supervisorctl update"
```

---

### 步骤 9: 重启服务

```bash
# 重启 AI 助理服务
ssh ai-server "sudo supervisorctl restart ai-assistant"

# 检查状态
ssh ai-server "sudo supervisorctl status ai-assistant"

# 查看日志
ssh ai-server "tail -50 /var/log/ai-assistant.log"
```

---

## 🧪 验证测试

### 1. 测试 Python 后端

```bash
# 访问服务器
curl http://47.109.148.176/ai/

# 应该返回登录页面 HTML
```

### 2. 测试 iOS 项目

```bash
cd ~/Documents/GJ/编程/ai助理new/ai-assistant-mobile
flutter build ios --debug --no-codesign

# 在 Xcode 中打开并运行
open ios/Runner.xcworkspace
```

### 3. 测试循环提醒功能 (验证 reminders 包)

1. 在 iOS 应用中创建提醒: "每天9:00提醒我吃药"
2. 打开 iPhone 系统"提醒事项" APP
3. 检查提醒是否显示"重复：每天"

---

## ⚠️ 关键注意事项

### 1. 修改的 reminders 包

- **最高优先级恢复**
- **必须在 flutter pub get 之前恢复**
- **不要运行 flutter pub upgrade reminders**

### 2. 敏感信息

- MySQL 密码: gyq3160GYQ3160
- API 密钥: 见 backend/ai_config.json
- 建议恢复后立即修改密码

### 3. Xcode 签名证书

- 签名证书不在备份中
- 需要手动导入开发证书
- 或在 Apple Developer 重新下载

### 4. SSH 密钥

- SSH 密钥不在备份中
- 需要重新配置 ai-server 免密登录:
  ```bash
  cat ~/.ssh/id_rsa.pub | ssh ai-server "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
  ```

---

## 🚨 故障排查

### 问题 1: Flutter 构建失败提示 recurrence 字段不存在

**原因**: reminders 包未正确恢复

**解决**:
```bash
# 重新恢复 reminders 包
cp -r dependencies/reminders-2.0.2-modified \
  ~/.pub-cache/hosted/pub.flutter-io.cn/reminders-2.0.2

# 清理并重建
flutter clean
flutter pub get
```

### 问题 2: 数据库恢复失败

**原因**: 数据库可能已存在

**解决**:
```bash
# 删除现有数据库
ssh ai-server "mysql -u root -pgyq3160GYQ3160 -e 'DROP DATABASE IF EXISTS ai_assistant;'"
ssh ai-server "mysql -u root -pgyq3160GYQ3160 -e 'CREATE DATABASE ai_assistant CHARACTER SET utf8mb4;'"

# 重新恢复
scp database/full_backup.sql ai-server:/tmp/
ssh ai-server "mysql -u root -pgyq3160GYQ3160 ai_assistant < /tmp/full_backup.sql"
```

### 问题 3: Nginx 配置加载失败

**原因**: 配置文件语法错误

**解决**:
```bash
# 测试配置
ssh ai-server "sudo nginx -t"

# 查看错误日志
ssh ai-server "sudo cat /var/log/nginx/error.log"
```

---

## 📞 支持

如遇到其他问题，请检查:
1. `MODIFICATIONS.md` - 第三方依赖修改说明
2. `database/statistics.txt` - 数据库统计信息
3. `config/service_status.txt` - 服务状态

---

**恢复完成后建议**:
1. ✅ 测试所有核心功能
2. ✅ 验证循环提醒功能
3. ✅ 修改数据库密码
4. ✅ 创建新的完整备份

---
Generated by AI Assistant Complete Backup System
Backup Date: $(date '+%Y-%m-%d %H:%M:%S')
EOFRECOVERY

echo -e "${GREEN}✓${NC} RECOVERY_GUIDE.md"

# 生成备份信息
cat > "${TEMP_DIR}/BACKUP_INFO.txt" << EOFINFO
========================================
AI助理系统 - 完整备份信息
========================================
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份名称: ${BACKUP_NAME}
服务器: 47.109.148.176

========================================
备份内容统计
========================================
Python后端: ${CODE_COUNT} 个文件
Flutter项目: ${DART_FILES:-0} 个Dart文件 (${FLUTTER_SIZE:-0})
Electron项目: ${ELECTRON_SIZE:-0}
修改的依赖: ${REMINDERS_SIZE:-0}
上传文件: $((${AVATARS_COUNT:-0} + ${IMAGES_COUNT:-0} + ${FILES_COUNT:-0})) 个 (${TOTAL_UPLOADS_SIZE:-0})
数据库: ${DB_SIZE}

========================================
关键文件清单
========================================
EOFINFO

find "${TEMP_DIR}" -type f | sed "s|${TEMP_DIR}/||" | sort >> "${TEMP_DIR}/BACKUP_INFO.txt"

echo -e "${GREEN}✓${NC} BACKUP_INFO.txt"

# 打包压缩代码和项目文件
echo ""
echo "正在打包代码和项目文件 (可能需要几分钟)..."

# 创建有意义的子目录名
ARCHIVE_DIR_NAME="ai-assistant-backup-${TIMESTAMP}"
mkdir -p "${TEMP_DIR}/${ARCHIVE_DIR_NAME}"

# 移动所有内容到子目录
mv "${TEMP_DIR}"/backend "${TEMP_DIR}/${ARCHIVE_DIR_NAME}/" 2>/dev/null
mv "${TEMP_DIR}"/projects "${TEMP_DIR}/${ARCHIVE_DIR_NAME}/" 2>/dev/null
mv "${TEMP_DIR}"/dependencies "${TEMP_DIR}/${ARCHIVE_DIR_NAME}/" 2>/dev/null
mv "${TEMP_DIR}"/config "${TEMP_DIR}/${ARCHIVE_DIR_NAME}/" 2>/dev/null
mv "${TEMP_DIR}"/docs "${TEMP_DIR}/${ARCHIVE_DIR_NAME}/" 2>/dev/null

# 打包（包含顶层目录）
tar -czf "${BACKUP_DIR}/ai-assistant-backup-${TIMESTAMP}.tar.gz" -C "${TEMP_DIR}" "${ARCHIVE_DIR_NAME}" 2>/dev/null

if [ -f "${BACKUP_DIR}/ai-assistant-backup-${TIMESTAMP}.tar.gz" ]; then
    CODE_BACKUP_SIZE=$(du -sh "${BACKUP_DIR}/ai-assistant-backup-${TIMESTAMP}.tar.gz" | cut -f1)
    echo -e "${GREEN}✅ 代码打包完成${NC}"
    echo -e "${GREEN}📦 代码备份: ${CODE_BACKUP_SIZE}${NC}"
else
    echo -e "${RED}❌ 代码打包失败${NC}"
    exit 1
fi

# 复制数据库备份
echo ""
echo "正在复制数据库备份..."
if [ -f "${TEMP_DIR}/database/full_backup.sql" ]; then
    cp "${TEMP_DIR}/database/full_backup.sql" "${BACKUP_DIR}/ai_assistant_db_backup_${TIMESTAMP}.sql"
    DB_BACKUP_SIZE=$(du -sh "${BACKUP_DIR}/ai_assistant_db_backup_${TIMESTAMP}.sql" | cut -f1)
    echo -e "${GREEN}✅ 数据库备份完成${NC}"
    echo -e "${GREEN}📊 数据库备份: ${DB_BACKUP_SIZE}${NC}"
fi

# 生成备份说明文件
echo ""
echo "正在生成备份说明..."
cat > "${BACKUP_DIR}/备份说明.txt" << EOFNOTE
========================================
AI助理系统 - 标准备份
========================================
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份类型: 标准备份（不含用户上传文件）

========================================
备份内容
========================================
1. ai-assistant-backup-${TIMESTAMP}.tar.gz
   - Python后端代码 (${CODE_COUNT} 个文件)
   - Flutter移动端项目 (${DART_FILES:-0} 个Dart文件)
   - Electron桌面端项目 (${ELECTRON_SIZE:-0})
   - 修改的依赖包 (reminders-2.0.2)
   - 配置文件 (Nginx, Supervisor)
   - 文档文件

2. ai_assistant_db_backup_${TIMESTAMP}.sql
   - MySQL数据库完整备份
   - 数据库大小: ${DB_SIZE}

========================================
恢复方法
========================================
1. 解压代码备份：
   tar -xzf ai-assistant-backup-${TIMESTAMP}.tar.gz

2. 恢复数据库：
   mysql -u root -p ai_assistant < ai_assistant_db_backup_${TIMESTAMP}.sql

3. 恢复修改的依赖包：
   详见解压后的 dependencies/MODIFICATIONS.md

========================================
重要提醒
========================================
⚠️ 此备份不包含 uploads/ 用户上传文件
⚠️ reminders-2.0.2 包的修改必须在 flutter pub get 之前恢复
⚠️ 详细恢复指南请查看解压后的 RECOVERY_GUIDE.md

备份完成时间: $(date '+%Y-%m-%d %H:%M:%S')
========================================
EOFNOTE

echo -e "${GREEN}✓${NC} 备份说明已生成"

# 清理临时目录
rm -rf "${TEMP_DIR}"
echo -e "${GREEN}✓${NC} 临时文件已清理"

# 计算总备份大小
BACKUP_TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)

# ========================================
# 上传到云服务器
# ========================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}上传备份到云服务器${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 创建服务器备份目录
sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "mkdir -p ${SERVER_BAK_DIR}" 2>/dev/null

# 打包备份目录用于上传
echo "正在打包备份目录..."
cd "${LOCAL_BAK_DIR}"
tar -czf "${BACKUP_DIR_NAME}.tar.gz" "${BACKUP_DIR_NAME}" 2>/dev/null

if [ -f "${BACKUP_DIR_NAME}.tar.gz" ]; then
    UPLOAD_SIZE=$(du -sh "${BACKUP_DIR_NAME}.tar.gz" | cut -f1)
    echo -e "${GREEN}✓${NC} 打包完成: ${UPLOAD_SIZE}"

    echo "正在上传 (可能需要几分钟)..."
    sshpass -p "${SERVER_PASSWORD}" scp -o StrictHostKeyChecking=no "${BACKUP_DIR_NAME}.tar.gz" ${SERVER_USER}@${SERVER_IP}:${SERVER_BAK_DIR}/ 2>/dev/null

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 上传成功${NC}"
        echo -e "${GREEN}📍 服务器路径: ${SERVER_IP}:${SERVER_BAK_DIR}/${BACKUP_DIR_NAME}.tar.gz${NC}"

        # 删除上传用的临时压缩包
        rm -f "${BACKUP_DIR_NAME}.tar.gz"

        # 检查云端备份数量
        CLOUD_COUNT=$(sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} "ls -1 ${SERVER_BAK_DIR}/backup-*.tar.gz 2>/dev/null | wc -l" | tr -d ' ')
        echo -e "${GREEN}☁️  云端备份数量: ${CLOUD_COUNT} 个${NC}"
    else
        echo -e "${YELLOW}⚠️  上传失败，但本地备份已完成${NC}"
        rm -f "${BACKUP_DIR_NAME}.tar.gz"
    fi
fi

cd - > /dev/null

# ========================================
# 完成
# ========================================
echo ""
echo "=========================================="
echo -e "${GREEN}🎉🎉🎉 标准系统备份全部完成！${NC}"
echo "=========================================="
echo ""
echo -e "${CYAN}📦 本地备份${NC}"
echo "  目录: ${BACKUP_DIR}"
echo "  大小: ${BACKUP_TOTAL_SIZE}"
echo "  文件:"
echo "    - ai-assistant-backup-${TIMESTAMP}.tar.gz (代码和项目)"
echo "    - ai_assistant_db_backup_${TIMESTAMP}.sql (数据库)"
echo "    - 备份说明.txt"
echo ""
echo -e "${CYAN}☁️  云端备份${NC}"
echo "  位置: ${SERVER_IP}:${SERVER_BAK_DIR}/"
echo "  文件: ${BACKUP_DIR_NAME}.tar.gz"
echo ""
echo -e "${CYAN}📊 备份内容${NC}"
echo "  Python后端: ${CODE_COUNT} 个文件"
echo "  Flutter项目: ${DART_FILES:-0} 个Dart文件"
echo "  Electron项目: ${ELECTRON_SIZE:-0}"
echo "  修改的依赖: reminders-2.0.2 (${REMINDERS_SIZE:-0})"
echo "  数据库: ${DB_SIZE}"
echo ""
echo -e "${CYAN}🔧 快速操作${NC}"
echo "  查看备份目录: ls -lh ${BACKUP_DIR}"
echo "  查看备份说明: cat ${BACKUP_DIR}/备份说明.txt"
echo "  解压代码备份: tar -xzf ${BACKUP_DIR}/ai-assistant-backup-${TIMESTAMP}.tar.gz -C /path/to/restore/"
echo "  恢复数据库: mysql -u root -p ai_assistant < ${BACKUP_DIR}/ai_assistant_db_backup_${TIMESTAMP}.sql"
echo ""
echo -e "${MAGENTA}⚠️  重要提醒${NC}"
echo "  1. 此备份不包含 uploads/ 用户上传文件"
echo "  2. 修改的 reminders-2.0.2 包已备份 - 这是最关键的依赖"
echo "  3. 恢复时必须先恢复此包，再运行 flutter pub get"
echo "  4. 详细恢复指南请查看 ${BACKUP_DIR}/备份说明.txt"
echo ""
echo "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# ========================================
# 备份建议
# ========================================
OLD_BACKUPS=$(ls -1d ${LOCAL_BAK_DIR}/backup-* 2>/dev/null | wc -l | tr -d ' ')
if [ "$OLD_BACKUPS" -gt 3 ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}💡 备份管理建议${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "本地有 ${OLD_BACKUPS} 个备份，建议："
    echo "  1. 保留最近 2-3 个备份"
    echo "  2. 重要版本备份重命名保存 (如: backup-循环提醒功能完成/)"
    echo "  3. 定期清理旧备份释放空间"
    echo ""
    echo "查看所有备份: ls -lth bak/"
    echo ""
fi

# 播放提示音
afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || true
