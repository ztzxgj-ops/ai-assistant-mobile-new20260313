# AI Assistant Desktop

macOS 桌面版 AI 助手客户端，使用 Electron + React 构建。

## 功能特性

- 🔐 用户登录认证
- 💬 实时聊天对话
- 🤖 连接到云端 AI 服务
- 💾 消息历史记录
- 🎨 现代化 UI 设计
- 🔄 自动重连机制

## 系统要求

- macOS 10.13+
- Node.js 14+
- npm 6+

## 安装

```bash
cd ai-assistant-desktop
npm install
```

## 开发

启动开发模式（同时运行 React 和 Electron）：

```bash
npm run dev
```

或分别运行：

```bash
# 终端1：启动 React 开发服务器
npm run react-start

# 终端2：启动 Electron（等待 React 启动后）
npm run electron-start
```

## 构建

构建 macOS 应用：

```bash
# 构建 DMG 安装程序
npm run build-dmg

# 或构建 ZIP 包
npm run build-mac
```

构建输出在 `dist/` 目录。

## 配置

### 服务器地址

编辑 `src/App.js` 中的 `API_BASE_URL`：

```javascript
const API_BASE_URL = 'http://47.109.148.176/ai';
```

## 项目结构

```
ai-assistant-desktop/
├── public/
│   ├── electron.js          # Electron 主进程
│   ├── preload.js           # 预加载脚本
│   ├── index.html           # HTML 模板
│   └── icon.png             # 应用图标
├── src/
│   ├── App.js               # 主应用组件
│   ├── App.css              # 应用样式
│   ├── index.js             # React 入口
│   └── index.css            # 全局样式
├── package.json             # 项目配置
└── README.md                # 本文件
```

## API 集成

应用连接到云端服务器的以下 API 端点：

- `POST /api/auth/login` - 用户登录
- `GET /api/user/profile` - 获取用户信息
- `GET /api/chats` - 获取聊天历史
- `POST /api/ai/chat` - 发送消息

## 故障排除

### 端口 3000 已被占用

```bash
lsof -i :3000
kill -9 <PID>
```

### 构建失败

```bash
rm -rf node_modules package-lock.json
npm install
npm run build-mac
```

### 连接服务器失败

检查：
1. 服务器地址是否正确
2. 网络连接是否正常
3. 服务器是否在线

## 许可证

MIT
