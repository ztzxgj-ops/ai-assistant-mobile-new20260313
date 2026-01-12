# AI Personal Assistant - Mac桌面应用开发指南

## 快速开始

### 环境要求

- macOS 12+
- Node.js 16+
- Python 3.8+
- 通义千问API Key（从阿里云控制台获取）

### 安装依赖

```bash
# 1. 进入项目目录
cd ai-assistant-electron

# 2. 安装Node.js依赖
npm install

# 3. 配置AI API（重要！）
cp backend/config/ai_config.json.example backend/config/ai_config.json
# 然后编辑 backend/config/ai_config.json，填入你的通义千问API Key
```

### 开发模式运行

```bash
# 直接启动Electron应用（会自动启动Python后端）
npm start
```

应用会：
1. 自动启动Python后端（监听随机端口）
2. 初始化SQLite数据库（存储在 `~/Library/Application Support/AIAssistant/data.db`）
3. 打开Electron窗口并加载登录页

### 第一次使用

1. 点击"注册"创建账户
2. 登录后即可开始使用AI助手

## 开发工作流

### 修改前端代码

前端文件位于 `frontend/` 目录：
- `login.html` - 登录/注册页面
- `index.html` - 主聊天界面
- `js/api.js` - API封装
- `css/` - 样式文件

修改后直接刷新窗口（Cmd+R）即可看到效果。

### 修改Python后端

后端文件位于 `backend/` 目录：
- `main.py` - HTTP服务器入口
- `sqlite_manager.py` - 数据库管理
- `user_manager.py` - 用户认证
- `ai_chat_assistant.py` - AI聊天逻辑

修改后需要重启应用（关闭窗口后 `npm start`）。

### 查看日志

- Electron日志：在终端窗口中查看
- Python后端日志：同样在终端中，带 `[Python]` 前缀
- 浏览器控制台：Cmd+Option+I 打开DevTools

## 打包为Mac应用

### 准备

```bash
# 安装PyInstaller（如果还没装）
pip3 install pyinstaller

# 打包Python后端为二进制文件
cd backend
pyinstaller main.py --onefile --name ai-backend \
  --add-data "config/db_schema.sql:config" \
  --hidden-import sqlite3 \
  --clean

# 验证生成的文件
ls -lh dist/ai-backend
```

### 打包Electron应用

```bash
# 返回项目根目录
cd ..

# 打包Mac应用（支持Intel和Apple Silicon）
npm run build:mac
```

输出文件：
- `dist/AI Personal Assistant.app` - 应用程序
- `dist/AI Personal Assistant-1.0.0.dmg` - 安装包

### 测试打包后的应用

```bash
# 直接运行.app
open "dist/mac/AI Personal Assistant.app"

# 或者安装dmg后测试
```

## 项目结构

```
ai-assistant-electron/
├── main.js                   # Electron主进程
├── preload.js                # IPC安全桥接
├── package.json              # 项目配置
├── electron-builder.json     # 打包配置
│
├── frontend/                 # 前端文件
│   ├── login.html           # 登录页
│   ├── index.html           # 主页面
│   ├── js/
│   │   ├── api.js           # API封装
│   │   └── chat.js          # 聊天逻辑
│   └── css/
│       └── mobile_ui_v5.css # 样式
│
├── backend/                  # Python后端
│   ├── main.py              # 入口文件
│   ├── sqlite_manager.py    # 数据库管理
│   ├── user_manager.py      # 用户管理
│   ├── ai_chat_assistant.py # AI助手
│   ├── reminder_scheduler.py# 提醒调度
│   ├── notification_service.py # 系统通知
│   ├── config/
│   │   ├── db_schema.sql    # 数据库schema
│   │   └── ai_config.json.example # 配置模板
│   └── requirements.txt     # Python依赖
│
├── resources/                # 应用资源（图标等）
└── dist/                     # 打包输出
```

## 技术架构

### 前端 → Electron → Python 通信流程

```
前端JavaScript
  ↓ window.electronAPI.chat(message)
Preload.js (IPC Bridge)
  ↓ ipcRenderer.invoke('api-request', ...)
Main.js (主进程)
  ↓ axios.post(http://localhost:PORT/api/ai/chat, ...)
Python HTTP Server (backend/main.py)
  ↓ AIAssistant.chat()
SQLite Database
```

### 数据存储

- **数据库文件**: `~/Library/Application Support/AIAssistant/data.db`
- **配置文件**: `backend/config/ai_config.json`
- **上传文件**: `~/Documents/AIAssistant/uploads/` (未来功能)

### 数据库表结构

1. **users** - 用户账号
2. **sessions** - 登录会话
3. **messages** - 聊天记录
4. **work_plans** - 工作计划
5. **reminders** - 提醒事项
6. **images** - 图片管理
7. **files** - 文件管理

## 常见问题

### Q: 启动时提示"后端服务未启动"？

A: 检查：
1. Python 3是否安装（`python3 --version`）
2. 查看终端错误日志
3. 确认`backend/main.py`文件存在

### Q: 无法登录？

A:
1. 先注册新账户
2. 检查数据库文件是否正常创建
3. 查看Python后端日志

### Q: AI回复总是出错？

A: 检查`backend/config/ai_config.json`：
- API Key是否正确
- 网络是否能访问dashscope.aliyuncs.com

### Q: 打包后的应用无法运行？

A:
1. 右键点击.app，选择"打开"（绕过Gatekeeper）
2. 检查`backend/dist/ai-backend`是否存在
3. 查看控制台应用的日志

## 下一步开发建议

### 功能完善

- [ ] 完整提取原assistant_web.py中的所有HTML模板
- [ ] 添加图片上传和展示功能
- [ ] 添加文件管理功能
- [ ] 实现工作计划可视化面板
- [ ] 添加提醒通知功能
- [ ] 支持语音输入（Web Speech API）
- [ ] 支持截图粘贴

### UI优化

- [ ] 添加深色模式
- [ ] 优化移动端适配
- [ ] 添加加载动画
- [ ] 改进消息渲染（支持Markdown）

### 性能优化

- [ ] 添加消息缓存
- [ ] 实现虚拟滚动（长消息列表）
- [ ] 优化SQLite查询性能

### Windows/Linux支持

- [ ] 修改数据目录路径（Windows: `%APPDATA%`, Linux: `~/.config`）
- [ ] 适配系统通知API
- [ ] 测试跨平台兼容性

## 许可证

MIT License

## 联系方式

如有问题，请通过以下方式联系：
- 提Issue到项目仓库
- 邮件：your-email@example.com
