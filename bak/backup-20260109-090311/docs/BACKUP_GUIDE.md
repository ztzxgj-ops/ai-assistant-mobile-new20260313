# AI助理系统自动备份工具使用指南

本工具提供了三种方式来备份云服务器的AI助理系统：Shell脚本、HTML网页、Python GUI程序。

## 📦 备份内容

✅ **包含的内容**：
- 所有Python源代码 (*.py)
- 配置文件 (*.json)
- 文档文件 (*.md)
- 部署脚本 (deploy/)
- MySQL数据库完整备份

❌ **排除的内容**：
- uploads/ 目录（图片和文件上传）
- __pycache__/ 目录
- *.pyc 编译文件

## 🚀 使用方法

### 方式一：Shell脚本（推荐）

**特点**：功能最完整，执行速度最快

```bash
# 进入项目目录
cd ~/Documents/GJ/编程/ai助理new

# 执行备份脚本
./backup_server.sh
```

**功能**：
- ✅ 自动备份代码和数据库
- ✅ 彩色日志输出
- ✅ 进度显示
- ✅ 自动清理旧备份（保留最近10个）
- ✅ 生成备份说明文件
- ✅ 完成后播放提示音

---

### 方式二：HTML网页工具

**特点**：界面美观，易于使用

```bash
# 在浏览器中打开
open ~/Documents/GJ/编程/ai助理new/backup_tool.html
```

**功能**：
- ✅ 可视化进度条
- ✅ 实时日志显示
- ✅ 备份历史记录
- ✅ 响应式设计
- ⚠️ 实际执行仍需在终端运行脚本

**使用步骤**：
1. 在浏览器中打开 `backup_tool.html`
2. 点击"开始备份"按钮查看模拟流程
3. 根据提示在终端执行实际备份命令

---

### 方式三：Python GUI程序

**特点**：独立程序，功能强大

```bash
# 运行GUI程序
python3 backup_tool.py
```

**功能**：
- ✅ 图形界面操作
- ✅ 实时日志输出
- ✅ 进度条显示
- ✅ 备份历史管理
- ✅ 一键打开备份目录
- ✅ 完成提示音

**系统要求**：
- Python 3.x
- tkinter（macOS自带）

---

## 📂 备份文件位置

### 云端服务器（临时）

```
/tmp/ai-assistant-backup-YYYYMMDD-HHMMSS.tar.gz
/tmp/ai_assistant_db_backup_YYYYMMDD-HHMMSS.sql
```

### 本地备份目录

```
~/Documents/GJ/编程/ai助理new/bak/
├── ai-assistant-backup-YYYYMMDD-HHMMSS.tar.gz  # 代码备份
├── ai_assistant_db_backup_YYYYMMDD-HHMMSS.sql  # 数据库备份
└── 备份说明-YYYYMMDD.txt                        # 备份说明
```

---

## 🔄 恢复备份

### 恢复代码文件

```bash
# 解压备份到服务器
tar -xzf ai-assistant-backup-YYYYMMDD-HHMMSS.tar.gz -C /var/www/ai-assistant/
```

### 恢复数据库

```bash
# 恢复MySQL数据库
mysql -u ai_assistant -p'ai_assistant_2024' ai_assistant < ai_assistant_db_backup_YYYYMMDD-HHMMSS.sql
```

### 重启服务

```bash
# 重启AI助手服务
sudo supervisorctl restart ai-assistant
```

---

## ⚙️ 配置说明

所有三个工具共享相同的配置：

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 服务器IP | 47.109.148.176 | 云服务器地址 |
| 服务器路径 | /var/www/ai-assistant | AI助手安装目录 |
| 本地备份目录 | ~/Documents/GJ/编程/ai助理new/bak | 本地备份存储位置 |
| 数据库名 | ai_assistant | MySQL数据库名 |
| 保留数量 | 10 | 自动清理时保留的备份数量 |

---

## 🔧 自动化备份

### 使用 cron 定时任务

每天凌晨2点自动备份：

```bash
# 编辑crontab
crontab -e

# 添加以下行
0 2 * * * /Users/a1-6/Documents/GJ/编程/ai助理new/backup_server.sh >> /tmp/backup.log 2>&1
```

### 使用 launchd (macOS推荐)

创建 `~/Library/LaunchAgents/com.ai-assistant.backup.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ai-assistant.backup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/a1-6/Documents/GJ/编程/ai助理new/backup_server.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/ai-assistant-backup.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/ai-assistant-backup-error.log</string>
</dict>
</plist>
```

加载任务：

```bash
launchctl load ~/Library/LaunchAgents/com.ai-assistant.backup.plist
```

---

## 📊 备份统计

使用以下命令查看备份统计：

```bash
# 查看备份数量
ls -l ~/Documents/GJ/编程/ai助理new/bak/*.tar.gz | wc -l

# 查看总大小
du -sh ~/Documents/GJ/编程/ai助理new/bak/

# 查看最新备份
ls -lt ~/Documents/GJ/编程/ai助理new/bak/*.tar.gz | head -1
```

---

## ❓ 常见问题

### Q: 提示"sshpass: command not found"

**A:** 需要安装sshpass工具：

```bash
brew install sshpass
```

### Q: 备份失败，提示"Permission denied"

**A:** 检查SSH密码是否正确，或者SSH密钥配置

### Q: 如何修改备份保留数量？

**A:** 编辑 `backup_server.sh`，修改 `cleanup_old_backups()` 函数中的数字10

### Q: Python GUI程序打不开

**A:** 确保安装了tkinter：

```bash
python3 -c "import tkinter"
```

### Q: 想要备份uploads目录怎么办？

**A:** 修改 `backup_server.sh` 中的tar命令，删除 `--exclude='uploads'`

---

## 📞 技术支持

如有问题，请查看：
- 备份日志：终端输出或GUI程序日志窗口
- 服务器日志：`sudo supervisorctl tail ai-assistant`
- 错误日志：`/tmp/ai-assistant-backup-error.log`

---

## 📝 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0 | 2026-01-08 | 初始版本，包含三种备份方式 |

---

**提示**：建议定期测试恢复流程，确保备份可用性！

---

## 🌐 网页版真实备份（新增）

### 特点
- ✅ **真实执行备份**：不是模拟，会实际调用备份脚本
- ✅ **可视化界面**：美观的Web界面
- ✅ **实时日志**：查看备份脚本的实时输出
- ✅ **备份历史**：自动显示本地备份文件
- ✅ **进度跟踪**：实时更新备份进度

### 使用方法

**方式一：一键启动（推荐）**

```bash
cd ~/Documents/GJ/编程/ai助理new
./start_backup_web.sh
```

脚本会自动：
1. 启动Web服务器（端口8888）
2. 2秒后自动打开浏览器
3. 访问 http://127.0.0.1:8888

**方式二：手动启动**

```bash
# 终端1：启动Web服务器
cd ~/Documents/GJ/编程/ai助理new
python3 backup_web_server.py

# 终端2或浏览器：访问
open http://127.0.0.1:8888
```

### 操作步骤

1. 点击"🎯 开始备份"按钮
2. 实时查看备份日志输出
3. 等待备份完成（状态变为"🟢 服务就绪"）
4. 查看备份历史确认文件已创建
5. 可点击"📂 打开备份目录"查看备份文件

### 技术架构

```
浏览器 (backup_tool_live.html)
    ↓ HTTP请求
本地Web服务器 (backup_web_server.py:8888)
    ↓ 调用Shell脚本
备份脚本 (backup_server.sh)
    ↓ SSH连接
云服务器 (47.109.148.176)
```

### API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回HTML页面 |
| `/api/backup` | GET | 启动备份任务 |
| `/api/status` | GET | 查询备份状态 |
| `/api/history` | GET | 获取备份历史 |

### 停止服务器

在运行 `python3 backup_web_server.py` 的终端按 `Ctrl+C`

---

## 📊 备份方式对比

| 功能 | Shell脚本 | HTML网页(旧) | HTML网页(新) | Python GUI |
|------|-----------|--------------|--------------|------------|
| 真实备份 | ✅ | ❌ | ✅ | ✅ |
| 可视化界面 | ❌ | ✅ | ✅ | ✅ |
| 实时日志 | ✅ | ❌ | ✅ | ✅ |
| 进度显示 | ✅ | ✅ | ✅ | ✅ |
| 备份历史 | ❌ | ✅ | ✅ | ✅ |
| 无需安装 | ✅ | ✅ | ❌(需Web服务器) | ❌(需tkinter) |
| 推荐指数 | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**推荐使用**：
- 快速备份：Shell脚本
- 最佳体验：HTML网页(新) + Web服务器
- 离线使用：Python GUI

---

## 🔧 故障排除

### 网页版显示"连接服务器失败"

**原因**：Web服务器未启动

**解决**：
```bash
cd ~/Documents/GJ/编程/ai助理new
python3 backup_web_server.py
```

### 网页版一直显示"备份进行中"

**原因**：备份脚本执行时间较长

**解决**：等待或查看终端输出确认进度

### 备份后文件在哪里？

**位置**：
```
~/Documents/GJ/编程/ai助理new/bak/
```

**查看**：
```bash
ls -lh ~/Documents/GJ/编程/ai助理new/bak/
```

---

更新日期：2026-01-08
