# 🚀 AI Assistant Desktop - 快速参考

## 📍 项目位置
```
/Users/gj/编程/ai助理new/ai-assistant-desktop/
```

## ⚡ 快速命令

### 开发
```bash
cd ai-assistant-desktop
npm install          # 首次安装依赖
npm run dev          # 启动开发模式
```

### 构建
```bash
npm run build-dmg    # 构建 DMG 安装程序
npm run build-mac    # 构建 ZIP 包
```

### 清理
```bash
npm run react-eject  # 弹出 React 配置（不可逆）
```

## 📂 关键文件

| 文件 | 用途 |
|------|------|
| `src/App.js` | 主应用逻辑（登录、聊天） |
| `src/App.css` | 应用样式 |
| `public/electron.js` | Electron 主进程 |
| `package.json` | 项目配置和依赖 |

## 🔧 常见修改

### 修改服务器地址
编辑 `src/App.js` 第 5 行：
```javascript
const API_BASE_URL = 'http://your-server.com/ai';
```

### 修改应用名称
编辑 `package.json`：
```json
{
  "name": "your-app-name",
  "productName": "Your App Name"
}
```

### 修改窗口大小
编辑 `public/electron.js` 第 8-9 行：
```javascript
width: 1200,   // 宽度
height: 800    // 高度
```

## 📚 文档

- `README.md` - 项目概览和使用说明
- `SETUP.md` - 详细的设置和自定义指南
- `DEPLOYMENT.md` - 构建和部署流程

## 🎯 功能清单

- ✅ 用户登录认证
- ✅ 实时聊天
- ✅ 消息历史
- ✅ 用户信息显示
- ✅ 现代化 UI
- ✅ 错误处理
- ✅ 自动重连

## 🔐 安全特性

- ✅ 上下文隔离
- ✅ 预加载脚本
- ✅ Token 认证
- ✅ 禁用 Node 集成

## 📦 依赖

- **Electron** 27.0.0 - 桌面应用框架
- **React** 18.2.0 - UI 框架
- **Axios** 1.6.0 - HTTP 客户端
- **Electron Builder** 24.6.4 - 应用打包

## 🐛 故障排除

### 端口 3000 被占用
```bash
lsof -i :3000
kill -9 <PID>
```

### 依赖安装失败
```bash
rm -rf node_modules package-lock.json
npm install
```

### 构建失败
```bash
npm run react-build
npm run build-dmg
```

## 📞 API 端点

```
POST   /api/auth/login          # 登录
GET    /api/user/profile        # 用户信息
GET    /api/chats               # 聊天历史
POST   /api/ai/chat             # 发送消息
```

所有请求需要 `Authorization: Bearer <token>` 头。

## 🎨 UI 配色

- 主色：`#667eea` (紫蓝)
- 辅色：`#764ba2` (深紫)
- 背景：`#f5f5f5` (浅灰)
- 用户消息：`#667eea` (紫蓝)
- 助手消息：`#f0f0f0` (浅灰)

## 📊 项目统计

- 文件数：13
- 代码行数：~1300
- 依赖数：5 个主要依赖
- 构建时间：5-10 分钟

## ✅ 下一步

1. [ ] 运行 `npm install`
2. [ ] 运行 `npm run dev` 测试
3. [ ] 自定义应用图标
4. [ ] 修改服务器地址（如需要）
5. [ ] 构建 DMG 安装程序
6. [ ] 测试安装程序
7. [ ] 部署到用户

---

**提示：** 首次运行 `npm install` 可能需要 3-5 分钟。
