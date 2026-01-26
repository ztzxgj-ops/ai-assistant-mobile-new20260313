# Mac备忘录同步服务 - 使用说明

## 功能说明

这个脚本会在您的Mac后台运行，定期从云服务器同步工作任务到本地Notes.app（备忘录）。

## 使用步骤

### 1. 配置用户信息

编辑 `sync_config.json` 文件，填写您的用户名和密码：

```json
{
  "server_url": "http://47.109.148.176/ai/",
  "username": "您的用户名",
  "password": "您的密码",
  "sync_interval": 30
}
```

### 2. 安装依赖

```bash
pip3 install requests
```

### 3. 启动同步服务

```bash
./start_sync.sh
```

或者直接运行：

```bash
python3 sync_notes_local.py
```

### 4. 停止同步服务

按 `Ctrl+C` 停止

## 工作原理

1. **定期同步**：每30秒从云服务器获取任务列表
2. **自动创建**：为新任务在Notes.app中创建备忘录
3. **自动删除**：任务完成或删除后，自动删除对应的备忘录
4. **状态跟踪**：使用 `sync_notes_state.json` 记录已同步的任务

## 备忘录格式

```
📋 任务标题

任务详细内容

⏰ 截止: 2026-01-25
🔥 优先级: 高
```

## 注意事项

1. **保持运行**：同步服务需要保持运行才能实时同步
2. **网络连接**：需要能访问云服务器（47.109.148.176）
3. **Notes.app**：会自动打开Notes.app应用
4. **安全性**：配置文件包含密码，请妥善保管

## 后台运行（可选）

如果想让同步服务在后台持续运行：

```bash
# 使用 nohup 后台运行
nohup python3 sync_notes_local.py > sync.log 2>&1 &

# 查看日志
tail -f sync.log

# 停止后台服务
ps aux | grep sync_notes_local.py
kill <进程ID>
```

## 开机自启动（可选）

创建 LaunchAgent 配置文件：

```bash
# 创建配置文件
cat > ~/Library/LaunchAgents/com.ai.notessync.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ai.notessync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/gj/编程/ai助理new/sync_notes_local.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/gj/编程/ai助理new/sync.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/gj/编程/ai助理new/sync_error.log</string>
</dict>
</plist>
EOF

# 加载服务
launchctl load ~/Library/LaunchAgents/com.ai.notessync.plist

# 卸载服务
launchctl unload ~/Library/LaunchAgents/com.ai.notessync.plist
```

## 故障排查

### 问题1：登录失败
- 检查用户名密码是否正确
- 检查网络连接
- 检查服务器是否可访问

### 问题2：备忘录未创建
- 检查Notes.app是否正常运行
- 查看同步日志中的错误信息
- 确认任务状态为pending或in_progress

### 问题3：同步状态异常
- 删除 `sync_notes_state.json` 文件重新同步
- 手动清理Notes.app中的旧备忘录

## 文件说明

- `sync_notes_local.py` - 同步脚本主程序
- `sync_config.json` - 配置文件（包含用户名密码）
- `sync_notes_state.json` - 同步状态文件（自动生成）
- `start_sync.sh` - 启动脚本
- `README_SYNC.md` - 本说明文件
