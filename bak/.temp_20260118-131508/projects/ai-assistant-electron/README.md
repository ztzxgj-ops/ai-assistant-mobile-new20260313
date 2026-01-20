# AI个人助理 - Electron桌面版

> 连接云服务器版本，无需本地安装Python和MySQL

## 特点

✨ **独立桌面应用** - 不依赖浏览器，原生窗口体验
☁️ **云端数据** - 连接云服务器，数据跨设备同步
🎨 **系统集成** - 系统托盘、原生通知、Dock图标
🔒 **安全可靠** - HTTPS连接，Token认证
📱 **跨平台** - 支持Mac、Windows、Linux

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 运行应用

```bash
npm start
```

### 3. 打包应用

```bash
# Mac版本
npm run build:mac

# Windows版本
npm run build:win

# Linux版本
npm run build:linux
```

## 打包输出

打包完成后，安装包将在 `dist/` 目录中：

- **Mac**: `AI个人助理.dmg` 和 `AI个人助理.app.zip`
- **Windows**: `AI个人助理 Setup.exe` 和 `AI个人助理 Portable.exe`
- **Linux**: `AI个人助理.AppImage` 和 `AI个人助理.deb`

## 功能特性

### 桌面功能
- ✅ 系统托盘 - 最小化到托盘，右键菜单
- ✅ 开机自启（可选）
- ✅ 快捷键唤醒
- ✅ 桌面通知
- ✅ Mac原生标题栏

### Web功能（完全复用云端）
- ✅ AI智能对话
- ✅ 工作计划管理
- ✅ 提醒系统
- ✅ 文件上传下载
- ✅ 图片管理
- ✅ 语音输入
- ✅ 用户认证

## 技术架构

```
┌─────────────────────────────────────┐
│   Electron App (本地桌面应用)        │
│  ┌──────────────────────────────┐   │
│  │  Chromium WebView            │   │
│  │  加载云服务器Web页面           │   │
│  └──────────────────────────────┘   │
│            ↓ HTTP/HTTPS             │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│   云服务器 (47.109.148.176)        │
│  ┌──────────────────────────────┐   │
│  │  Python HTTP Server (8000)   │   │
│  │  - Web界面 (HTML/CSS/JS)     │   │
│  │  - REST API                  │   │
│  └──────────────────────────────┘   │
│            ↓                        │
│  ┌──────────────────────────────┐   │
│  │  MySQL Database              │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

## 项目结构

```
ai-assistant-electron/
├── main.js              # Electron主进程
├── preload.js           # 预加载脚本
├── package.json         # 项目配置
├── assets/              # 资源文件
│   └── icons/           # 应用图标
│       ├── icon.icns    # Mac图标
│       ├── icon.ico     # Windows图标
│       └── icon.png     # Linux图标
└── dist/                # 打包输出目录
```

## 配置说明

### 修改服务器地址

如果云服务器地址变更，修改 `main.js` 第10行：

```javascript
const CLOUD_SERVER_URL = 'http://你的服务器地址/ai/';
```

## 系统要求

### Mac
- macOS 12 (Monterey) 或更高版本
- 100MB+ 可用磁盘空间

### Windows
- Windows 10/11
- 100MB+ 可用磁盘空间

### Linux
- Ubuntu 20.04+ / Debian 11+
- 100MB+ 可用磁盘空间

## 开发调试

### 打开开发者工具

应用会自动在开发模式下打开DevTools。如需关闭，修改 `main.js` 第68-70行：

```javascript
// if (!app.isPackaged) {
//     mainWindow.webContents.openDevTools();
// }
```

### 查看日志

```bash
# Mac
~/Library/Logs/AI个人助理/
# Windows
%APPDATA%\AI个人助理\logs\
# Linux
~/.config/AI个人助理/logs/
```

## 常见问题

### Q: 无法连接到服务器？
A: 检查网络连接，确认服务器地址正确，服务器是否正常运行。

### Q: 打包后的应用很大？
A: Electron应用包含Chromium内核，约100-150MB是正常大小。

### Q: Mac提示"无法打开，因为它来自身份不明的开发者"？
A: 右键点击应用 → 选择"打开" → 点击"打开"确认。

### Q: Windows提示SmartScreen？
A: 点击"更多信息" → "仍要运行"。

## 更新日志

### v1.0.0 (2025-12-22)
- ✅ 首次发布
- ✅ 连接云服务器
- ✅ 系统托盘支持
- ✅ 跨平台打包

## License

MIT

## 联系方式

如有问题，请通过以下方式联系：
- Email: your@email.com
- GitHub: github.com/your-username

---

**注意**: 本应用需要网络连接才能使用，所有数据存储在云服务器上。
