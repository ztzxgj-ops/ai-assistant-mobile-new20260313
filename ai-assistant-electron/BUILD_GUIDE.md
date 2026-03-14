# macOS Electron 应用构建指南

## 快速开始

### 1. 基础构建
```bash
cd ai-assistant-electron
chmod +x build-macos.sh
./build-macos.sh
```

### 2. 完整构建（清理 + 安装 + 构建 + 签名）
```bash
./build-macos.sh --all
```

### 3. 构建并上传到服务器
```bash
./build-macos.sh --all --upload
```

## 脚本选项

| 选项 | 说明 |
|------|------|
| `-h, --help` | 显示帮助信息 |
| `-c, --clean` | 清理旧的构建文件 |
| `-i, --install` | 安装依赖 (npm install) |
| `-s, --sign` | 对应用进行代码签名 |
| `-n, --notarize` | 对应用进行公证（需要 Apple 开发者账户） |
| `-u, --upload` | 构建完成后上传到服务器 |
| `-v, --verbose` | 显示详细输出 |
| `-a, --all` | 执行所有步骤 |

## 常见用法

### 场景 1：开发测试
```bash
# 快速构建，不清理旧文件
./build-macos.sh
```

### 场景 2：发布版本
```bash
# 完整构建，包括签名
./build-macos.sh --all --sign
```

### 场景 3：部署到服务器
```bash
# 完整构建并上传
./build-macos.sh --all --upload
```

### 场景 4：调试构建
```bash
# 显示详细日志
./build-macos.sh --verbose
```

## 构建输出

构建完成后，文件位置：

```
ai-assistant-electron/
├── dist/                          # 构建输出目录
│   ├── AI个人助理.app            # macOS 应用
│   ├── AI个人助理-x64.dmg        # Intel 版本 DMG
│   ├── AI个人助理-arm64.dmg      # Apple Silicon 版本 DMG
│   └── AI个人助理-x64.zip        # ZIP 压缩包
└── build-output/                  # 构建报告和日志
    ├── build-report-*.md          # 构建报告
    └── build-*.log                # 构建日志
```

## 代码签名

### 自动签名
脚本会自动检测系统中的代码签名证书：

```bash
./build-macos.sh --sign
```

### 手动签名
如果需要使用特定的证书：

```bash
# 查看可用的证书
security find-identity -v -p codesigning

# 手动签名
codesign -s "证书名称" --deep --force "dist/AI个人助理.app"

# 验证签名
codesign -v "dist/AI个人助理.app"
```

## 公证（Notarization）

### 配置 Apple 账户
```bash
export APPLE_ID="your-apple-id@example.com"
export APPLE_PASSWORD="app-specific-password"
export APPLE_TEAM_ID="XXXXXXXXXX"
```

### 执行公证
```bash
./build-macos.sh --notarize
```

> **注意**：公证需要 Apple 开发者账户，且需要生成应用专用密码。

## 上传到服务器

### 配置 SSH 密钥
```bash
# 生成 SSH 密钥（如果还没有）
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""

# 复制公钥到服务器
ssh-copy-id root@47.109.148.176
```

### 上传应用
```bash
./build-macos.sh --upload
```

脚本会自动上传以下文件到服务器：
- `*.dmg` - DMG 安装包
- `*.zip` - ZIP 压缩包
- `*.app` - 应用包

## 故障排除

### 问题 1：npm 依赖安装失败
```bash
# 清理缓存并重新安装
./build-macos.sh --clean --install
```

### 问题 2：代码签名失败
```bash
# 检查可用的证书
security find-identity -v -p codesigning

# 如果没有证书，需要在 Xcode 中配置开发者账户
# Xcode → Preferences → Accounts → Add Apple ID
```

### 问题 3：构建超时
```bash
# 增加超时时间，使用详细模式
./build-macos.sh --verbose
```

### 问题 4：上传失败
```bash
# 检查 SSH 连接
ssh root@47.109.148.176 "echo 'SSH 连接正常'"

# 检查目标目录
ssh root@47.109.148.176 "ls -la /var/www/ai-assistant/builds"
```

## 日志查看

### 实时查看构建日志
```bash
tail -f build-output/build-*.log
```

### 查看构建报告
```bash
cat build-output/build-report-*.md
```

## 测试应用

### 运行应用
```bash
open dist/AI个人助理.app
```

### 验证应用签名
```bash
codesign -v dist/AI个人助理.app
```

### 检查应用信息
```bash
mdls dist/AI个人助理.app
```

## 分发应用

### 方式 1：DMG 文件
最常见的 macOS 应用分发方式：
1. 用户下载 DMG 文件
2. 双击打开 DMG
3. 拖拽应用到 Applications 文件夹

### 方式 2：ZIP 压缩包
轻量级分发方式：
1. 用户下载 ZIP 文件
2. 自动解压得到 .app 文件
3. 双击运行应用

### 方式 3：App Store
需要完整的代码签名和公证：
1. 运行 `./build-macos.sh --all --sign --notarize`
2. 在 App Store Connect 中提交应用
3. 等待审核

## 自动化部署

### 创建定时构建任务
```bash
# 每天晚上 8 点自动构建
0 20 * * * cd /Users/gj/编程/ai助理new/ai-assistant-electron && ./build-macos.sh --all --upload
```

### 集成到 CI/CD
```yaml
# GitHub Actions 示例
name: Build macOS App
on: [push]
jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
      - run: ./build-macos.sh --all
      - uses: actions/upload-artifact@v2
        with:
          name: macos-app
          path: dist/
```

## 环境变量

脚本支持以下环境变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APPLE_ID` | Apple ID 邮箱 | 无 |
| `APPLE_PASSWORD` | 应用专用密码 | 无 |
| `APPLE_TEAM_ID` | Team ID | 无 |

## 性能优化

### 加快构建速度
```bash
# 跳过清理步骤
./build-macos.sh --install

# 只构建 ARM64 版本（Apple Silicon）
# 编辑 electron-builder.json，修改 arch 配置
```

### 减小应用大小
```bash
# 在 electron-builder.json 中配置
"files": [
  "main.js",
  "preload.js",
  "assets/**/*",
  "package.json"
]
```

## 更新应用

### 更新 Electron 版本
```bash
npm install electron@latest
./build-macos.sh --clean --install
```

### 更新 electron-builder
```bash
npm install electron-builder@latest
./build-macos.sh
```

## 支持和反馈

如遇到问题，请：
1. 查看构建日志：`build-output/build-*.log`
2. 查看构建报告：`build-output/build-report-*.md`
3. 运行详细模式：`./build-macos.sh --verbose`
