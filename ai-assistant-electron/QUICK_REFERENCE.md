# macOS Electron 应用自动化构建系统

## 📋 概述

这是一套完整的 macOS Electron 应用自动化构建系统，包含以下功能：

- ✅ 自动化编译和打包
- ✅ 代码签名和公证
- ✅ 自动上传到服务器
- ✅ 详细的构建日志和报告
- ✅ 快速命令和快捷方式
- ✅ 灵活的配置系统

## 📁 文件结构

```
ai-assistant-electron/
├── build-macos.sh          # 主构建脚本（完整功能）
├── build-config.sh         # 构建配置文件（可自定义）
├── quick-build.sh          # 快速命令脚本（便捷操作）
├── BUILD_GUIDE.md          # 详细使用指南
├── QUICK_REFERENCE.md      # 快速参考（本文件）
├── package.json            # Node.js 项目配置
├── electron-builder.json   # Electron Builder 配置
├── main.js                 # Electron 主进程
├── preload.js              # Preload 脚本
├── frontend/               # 前端代码
├── backend/                # 后端代码
├── dist/                   # 构建输出目录
└── build-output/           # 构建日志和报告
```

## 🚀 快速开始

### 1. 基础构建（推荐新手）
```bash
cd ai-assistant-electron
./quick-build.sh build
```

### 2. 完整构建（推荐发布）
```bash
./quick-build.sh full
```

### 3. 构建并上传（推荐部署）
```bash
./quick-build.sh upload
```

## 📖 详细使用

### 主构建脚本 - build-macos.sh

**基础用法：**
```bash
./build-macos.sh [选项]
```

**常用选项：**
| 选项 | 说明 |
|------|------|
| `-h, --help` | 显示帮助 |
| `-c, --clean` | 清理旧文件 |
| `-i, --install` | 安装依赖 |
| `-s, --sign` | 代码签名 |
| `-u, --upload` | 上传服务器 |
| `-a, --all` | 执行所有步骤 |

**示例：**
```bash
# 快速构建
./build-macos.sh

# 完整构建
./build-macos.sh --all

# 构建并上传
./build-macos.sh --all --upload

# 显示详细日志
./build-macos.sh --verbose
```

### 快速命令脚本 - quick-build.sh

**用法：**
```bash
./quick-build.sh <命令>
```

**可用命令：**
| 命令 | 说明 |
|------|------|
| `build` | 快速构建 |
| `full` | 完整构建 |
| `upload` | 构建并上传 |
| `test` | 启动应用 |
| `logs` | 查看日志 |
| `report` | 查看报告 |
| `verify` | 验证签名 |
| `info` | 显示应用信息 |
| `clean` | 清理文件 |
| `clean-all` | 清理所有 |

**示例：**
```bash
./quick-build.sh build      # 快速构建
./quick-build.sh test       # 启动应用
./quick-build.sh logs       # 查看日志
./quick-build.sh upload     # 构建并上传
```

### 配置脚本 - build-config.sh

**查看配置：**
```bash
./build-config.sh
```

**自定义配置：**
编辑 `build-config.sh` 文件，修改以下变量：

```bash
# 应用信息
export APP_NAME="AI个人助理"
export BUNDLE_ID="com.aiassistant.app"
export APP_VERSION="1.0.0"

# 构建配置
export BUILD_OUTPUT_DIR="dist"
export TARGET_ARCHS="x64 arm64"

# 服务器配置
export SERVER_IP="47.109.148.176"
export SERVER_USER="root"
export SERVER_BUILD_DIR="/var/www/ai-assistant/builds"

# 代码签名
export SIGNING_IDENTITY=""  # 留空自动检测
export ENABLE_HARDENED_RUNTIME=true
```

## 🔧 常见任务

### 任务 1：开发测试
```bash
# 快速构建，不清理旧文件
./quick-build.sh build

# 启动应用测试
./quick-build.sh test
```

### 任务 2：发布版本
```bash
# 完整构建，包括签名
./quick-build.sh full

# 验证签名
./quick-build.sh verify
```

### 任务 3：部署到服务器
```bash
# 构建并上传
./quick-build.sh upload

# 或使用主脚本
./build-macos.sh --all --upload
```

### 任务 4：调试构建问题
```bash
# 显示详细日志
./build-macos.sh --verbose

# 查看最新日志
./quick-build.sh logs

# 查看构建报告
./quick-build.sh report
```

### 任务 5：清理和重新开始
```bash
# 清理构建文件
./quick-build.sh clean

# 清理所有文件（包括 node_modules）
./quick-build.sh clean-all

# 重新安装依赖
./quick-build.sh install
```

## 📊 构建输出

### 输出文件位置
```
dist/
├── AI个人助理.app           # macOS 应用
├── AI个人助理-x64.dmg      # Intel 版本 DMG
├── AI个人助理-arm64.dmg    # Apple Silicon 版本 DMG
└── AI个人助理-x64.zip      # ZIP 压缩包

build-output/
├── build-report-*.md        # 构建报告
└── build-*.log              # 构建日志
```

### 文件大小参考
- `.app` 文件：~500MB（包含 Electron 框架）
- `.dmg` 文件：~200MB（压缩后）
- `.zip` 文件：~150MB（压缩后）

## 🔐 代码签名

### 自动签名
```bash
./build-macos.sh --sign
```

脚本会自动检测系统中的代码签名证书。

### 手动签名
```bash
# 查看可用证书
security find-identity -v -p codesigning

# 手动签名
codesign -s "证书名称" --deep --force "dist/AI个人助理.app"

# 验证签名
./quick-build.sh verify
```

### 获取代码签名证书
1. 打开 Xcode
2. 菜单：Xcode → Preferences → Accounts
3. 添加 Apple ID
4. 点击 "Manage Certificates"
5. 创建新的开发者证书

## 📤 上传到服务器

### 配置 SSH 密钥
```bash
# 生成 SSH 密钥（如果还没有）
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""

# 复制公钥到服务器
ssh-copy-id root@47.109.148.176
```

### 上传应用
```bash
./quick-build.sh upload
```

或使用主脚本：
```bash
./build-macos.sh --all --upload
```

### 验证上传
```bash
# 检查服务器上的文件
ssh root@47.109.148.176 "ls -lh /var/www/ai-assistant/builds/"
```

## 🐛 故障排除

### 问题 1：npm 依赖安装失败
```bash
# 清理缓存
npm cache clean --force

# 重新安装
./quick-build.sh install
```

### 问题 2：代码签名失败
```bash
# 检查证书
security find-identity -v -p codesigning

# 如果没有证书，在 Xcode 中配置
# Xcode → Preferences → Accounts → Add Apple ID
```

### 问题 3：构建超时
```bash
# 使用详细模式查看进度
./build-macos.sh --verbose

# 检查磁盘空间
df -h

# 检查网络连接
ping 8.8.8.8
```

### 问题 4：上传失败
```bash
# 测试 SSH 连接
ssh root@47.109.148.176 "echo 'SSH 连接正常'"

# 检查目标目录
ssh root@47.109.148.176 "ls -la /var/www/ai-assistant/builds"

# 检查磁盘空间
ssh root@47.109.148.176 "df -h"
```

## 📝 日志和报告

### 查看日志
```bash
# 查看最新日志
./quick-build.sh logs

# 或手动查看
tail -f build-output/build-*.log
```

### 查看报告
```bash
# 查看最新报告
./quick-build.sh report

# 或手动查看
cat build-output/build-report-*.md
```

### 日志位置
```
build-output/
├── build-20260313-210500.log      # 构建日志
└── build-report-20260313-210500.md # 构建报告
```

## 🎯 最佳实践

### 1. 定期清理
```bash
# 每周清理一次
./quick-build.sh clean-all
./quick-build.sh install
```

### 2. 版本管理
```bash
# 更新版本号
# 编辑 package.json 中的 version 字段
# 编辑 build-config.sh 中的 APP_VERSION

# 提交版本更新
git add package.json build-config.sh
git commit -m "Bump version to 1.0.1"
```

### 3. 自动化部署
```bash
# 创建 cron 任务（每天晚上 8 点构建）
0 20 * * * cd /Users/gj/编程/ai助理new/ai-assistant-electron && ./quick-build.sh upload
```

### 4. 备份构建
```bash
# 保存重要的构建版本
cp -r dist dist-backup-$(date +%Y%m%d)
```

## 📚 相关文档

- **BUILD_GUIDE.md** - 详细的构建指南
- **package.json** - Node.js 项目配置
- **electron-builder.json** - Electron Builder 配置
- **DEVELOPMENT.md** - 开发指南

## 🔗 快速链接

- [Electron 官方文档](https://www.electronjs.org/docs)
- [electron-builder 文档](https://www.electron.build/)
- [macOS 代码签名指南](https://developer.apple.com/support/code-signing/)
- [Apple 公证指南](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)

## 💡 提示

- 首次构建可能需要 5-10 分钟，后续构建会更快
- 确保有足够的磁盘空间（至少 2GB）
- 构建前关闭其他占用 CPU 的应用
- 使用 `--verbose` 选项可以看到详细的构建过程

## 📞 支持

如遇到问题：
1. 查看构建日志：`./quick-build.sh logs`
2. 查看构建报告：`./quick-build.sh report`
3. 查看详细指南：`BUILD_GUIDE.md`
4. 运行详细模式：`./build-macos.sh --verbose`

---

**最后更新**: 2026-03-13
**版本**: 1.0.0
