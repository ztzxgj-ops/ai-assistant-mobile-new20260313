# 备份脚本快速参考

## 推荐使用的备份脚本

### ⭐ backup_uploads.sh（推荐日常使用）
**用途**: 备份所有上传文件（图片、头像、文档）

**特点**:
- ✅ 快速（仅备份uploads目录）
- ✅ 本地 + 云端双重备份
- ✅ 自动生成清单文件
- ✅ 适合每日自动备份

**使用**:
```bash
./backup_uploads.sh
```

**备份内容**:
- uploads/avatars/ (用户头像)
- uploads/images/ (聊天图片)
- uploads/files/ (上传文档)

**保存位置**:
- 本地: `bak/uploads_backup_YYYYMMDD_HHMMSS.tar.gz`
- 云端: `ai-server:/var/www/ai-assistant/backups/`

---

### ⭐⭐ backup_full.sh（推荐重大更新前使用）
**用途**: 完整系统备份（代码 + 数据库 + 配置 + 上传文件）

**特点**:
- ✅ 全面（包含所有数据）
- ✅ 从服务器备份数据库
- ✅ 备份Nginx和Supervisor配置
- ✅ 包含恢复指南

**使用**:
```bash
./backup_full.sh
```

**备份内容**:
1. 本地代码和配置文件
2. 所有上传文件
3. 服务器MySQL数据库
4. Nginx和Supervisor配置
5. 应用日志

**保存位置**:
- 本地: `bak/ai_assistant_full_backup_YYYYMMDD_HHMMSS.tar.gz`
- 云端: `ai-server:/var/www/ai-assistant/backups/`

---

## 其他备份脚本（已有）

### backup_auto.sh
**用途**: 在云服务器上创建备份并下载到本地

**特点**:
- 仅备份代码和数据库
- 不包含uploads目录
- 需配合backup_uploads.sh使用

---

## 快速对比

| 脚本 | 速度 | 完整性 | 推荐场景 |
|------|------|--------|---------|
| backup_uploads.sh | ⚡⚡⚡ 快 | 仅上传文件 | 每日备份 |
| backup_full.sh | ⚡ 慢 | 完整系统 | 重大更新前 |
| backup_auto.sh | ⚡⚡ 中 | 代码+数据库 | 服务器端备份 |

---

## 推荐备份策略

### 日常使用
```bash
# 每天自动备份上传文件
./backup_uploads.sh
```

### 重要操作前
```bash
# 重大更新前完整备份
./backup_full.sh
```

### 自动化配置
```bash
# 编辑crontab
crontab -e

# 添加定时任务
# 每天凌晨2点备份上传文件
0 2 * * * cd /Users/jry/gj/ai助理/xyMac && ./backup_uploads.sh >> logs/backup.log 2>&1

# 每周日凌晨3点完整备份
0 3 * * 0 cd /Users/jry/gj/ai助理/xyMac && ./backup_full.sh >> logs/backup.log 2>&1
```

---

## 查看和管理备份

### 查看本地备份
```bash
ls -lh bak/
```

### 验证备份内容
```bash
# 查看文件列表
tar -tzf bak/uploads_backup_*.tar.gz | head -20

# 查看备份清单
cat bak/uploads_backup_*_manifest.txt
```

### 查看云端备份
```bash
ssh ai-server "ls -lh /var/www/ai-assistant/backups/"
```

---

## 恢复备份

### 恢复上传文件
```bash
# 解压
tar -xzf bak/uploads_backup_20251221_130951.tar.gz

# 本地恢复
cp -r uploads/* ./uploads/

# 或恢复到服务器
scp -r uploads/* ai-server:/var/www/ai-assistant/uploads/
```

### 完整系统恢复
```bash
# 解压备份
tar -xzf bak/ai_assistant_full_backup_*.tar.gz

# 查看恢复指南
cat .temp_*/README.md
```

---

## 详细文档

完整使用指南请查看: **BACKUP_GUIDE.md**

---

## 最近备份记录

**测试备份** (2025-12-21 13:09):
- 备份文件: uploads_backup_20251221_130951.tar.gz
- 文件数量: 54个（19个头像 + 35个图片）
- 压缩大小: 36M
- 本地保存: ✅
- 云端保存: ✅

---

## 常见问题

**Q: 多久备份一次？**
A: 推荐每天自动备份上传文件，每周完整备份一次

**Q: 备份保存多久？**
A: 建议保留最近7天的日常备份，最近4周的完整备份

**Q: 如何恢复数据？**
A: 参考备份包内的README.md或BACKUP_GUIDE.md

**Q: 备份失败怎么办？**
A: 检查网络连接、磁盘空间和SSH配置

---

生成时间: 2025-12-21
