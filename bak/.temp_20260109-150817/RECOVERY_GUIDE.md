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
