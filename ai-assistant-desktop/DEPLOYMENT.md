# AI Assistant Desktop - 部署指南

## 📦 构建和部署流程

### 第一步：准备环境

```bash
cd ai-assistant-desktop
npm install
```

### 第二步：构建应用

#### 选项 A：构建 DMG 安装程序（推荐）

```bash
npm run build-dmg
```

输出：`dist/AI Assistant-1.0.0.dmg`

用户可以直接双击 DMG 文件安装应用。

#### 选项 B：构建 ZIP 包

```bash
npm run build-mac
```

输出：`dist/AI Assistant-1.0.0.zip`

用户解压后可直接运行应用。

### 第三步：测试应用

1. 打开 `dist/` 目录中的应用
2. 使用测试账户登录
3. 验证聊天功能正常

### 第四步：分发

#### 方式 1：直接分发 DMG
```bash
# 上传到服务器或云存储
scp dist/AI\ Assistant-1.0.0.dmg user@server:/path/to/downloads/
```

#### 方式 2：通过 GitHub Releases
```bash
# 创建 GitHub Release 并上传 DMG 文件
```

#### 方式 3：通过应用商店
- 需要 Apple Developer 账户
- 需要代码签名证书
- 需要 App Store 审核

## 🔐 代码签名（可选但推荐）

### 生成签名证书

```bash
# 1. 创建自签名证书（开发用）
security create-signing-identity-and-key

# 2. 或使用 Apple Developer 证书
# 从 developer.apple.com 下载证书
```

### 配置签名

编辑 `package.json` 中的 `build` 部分：

```json
{
  "build": {
    "mac": {
      "certificateFile": "path/to/certificate.p12",
      "certificatePassword": "password",
      "signingIdentity": "Developer ID Application: Your Name"
    }
  }
}
```

## 📋 发布清单

- [ ] 更新版本号（`package.json` 中的 `version`）
- [ ] 更新 `README.md` 中的版本信息
- [ ] 测试所有功能
- [ ] 验证服务器连接
- [ ] 构建应用
- [ ] 测试安装程序
- [ ] 创建发布说明
- [ ] 上传到分发渠道
- [ ] 通知用户

## 🚀 自动化部署

### 使用 GitHub Actions

创建 `.github/workflows/build.yml`：

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm install
      - run: npm run build-dmg
      - uses: softprops/action-gh-release@v1
        with:
          files: dist/*.dmg
```

## 📊 版本管理

### 语义化版本

遵循 `MAJOR.MINOR.PATCH` 格式：

- `1.0.0` - 初始版本
- `1.1.0` - 新功能
- `1.0.1` - Bug 修复
- `2.0.0` - 重大更新

### 更新版本

```bash
# 编辑 package.json
{
  "version": "1.1.0"
}

# 提交并标记
git add package.json
git commit -m "Bump version to 1.1.0"
git tag v1.1.0
git push origin main --tags
```

## 🔄 更新流程

### 用户端更新

1. 下载新版本 DMG
2. 打开 DMG 文件
3. 拖动应用到 Applications 文件夹
4. 旧版本会被替换

### 自动更新（高级）

可以集成 `electron-updater` 实现自动更新：

```bash
npm install electron-updater
```

编辑 `public/electron.js`：

```javascript
const { autoUpdater } = require('electron-updater');

app.on('ready', () => {
  autoUpdater.checkForUpdatesAndNotify();
  createWindow();
});
```

## 📝 发布说明模板

```markdown
# AI Assistant Desktop v1.1.0

## 新功能
- ✨ 添加了 XXX 功能
- ✨ 改进了 XXX 性能

## Bug 修复
- 🐛 修复了 XXX 问题
- 🐛 修复了 XXX 崩溃

## 已知问题
- ⚠️ XXX 功能在某些情况下可能不工作

## 安装
1. 下载 `AI Assistant-1.1.0.dmg`
2. 打开 DMG 文件
3. 拖动应用到 Applications 文件夹

## 系统要求
- macOS 10.13+
- 网络连接

## 反馈
如有问题，请联系 support@example.com
```

## 🆘 故障排除

### 构建失败

```bash
# 清理缓存
rm -rf node_modules package-lock.json
npm install

# 重新构建
npm run build-dmg
```

### 应用无法启动

1. 检查 macOS 版本是否满足要求
2. 检查网络连接
3. 查看应用日志：`~/Library/Logs/AI Assistant/`

### 无法连接到服务器

1. 验证服务器地址
2. 检查网络连接
3. 检查防火墙设置

## 📞 支持

- 文档：`README.md` 和 `SETUP.md`
- 问题报告：GitHub Issues
- 邮件支持：support@example.com

---

**提示：** 首次构建可能需要 5-10 分钟，请耐心等待。
