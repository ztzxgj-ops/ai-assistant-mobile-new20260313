# iOS APP 手动安装指南

> **准确北京时间：2025年12月23日 23:00**
> 适合希望完全控制安装过程的用户

---

## 📋 环境检查结果

**你的系统：**
- ✅ macOS 26.1
- ✅ Ruby 2.6.10
- ⚠️ Xcode命令行工具（建议安装完整Xcode）
- ❌ Flutter SDK（需要安装）
- ❌ CocoaPods（需要安装）

---

## 🎯 安装目标

1. ✅ Flutter SDK（跨平台移动开发框架）
2. ✅ CocoaPods（iOS依赖管理工具）
3. ✅ 配置环境变量
4. ✅ 验证安装成功

**预计时间：** 30-60分钟

---

## 📦 第一步：安装Homebrew（如果未安装）

Homebrew可以简化后续安装：

```bash
# 检查是否已安装Homebrew
brew --version

# 如果未安装，执行（需要密码）：
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装后按提示添加到PATH
```

---

## 🦋 第二步：安装Flutter SDK

### 方式A：使用Git克隆（推荐）

```bash
# 1. 清理可能存在的不完整目录
rm -rf ~/flutter

# 2. 克隆Flutter仓库（stable分支）
cd ~
git clone https://github.com/flutter/flutter.git -b stable

# 这会下载约500MB，需要5-10分钟
# 你会看到：
# Cloning into 'flutter'...
# Receiving objects: 100% ...
```

### 方式B：下载压缩包

```bash
# 1. 访问官网下载
# https://docs.flutter.dev/get-started/install/macos

# 2. 下载最新stable版本（Intel或Apple Silicon）

# 3. 解压到用户目录
cd ~
unzip ~/Downloads/flutter_macos_*.zip
```

### 配置Flutter环境变量

```bash
# 1. 确认Flutter目录存在
ls ~/flutter/bin/flutter

# 2. 添加到PATH（zsh用户）
echo '' >> ~/.zshrc
echo '# Flutter' >> ~/.zshrc
echo 'export PATH="$HOME/flutter/bin:$PATH"' >> ~/.zshrc

# 如果使用bash，编辑 ~/.bash_profile 替代 ~/.zshrc

# 3. 立即生效
source ~/.zshrc  # 或 source ~/.bash_profile

# 4. 验证安装
flutter --version

# 预期输出：
# Flutter 3.x.x • channel stable
```

### 运行Flutter诊断

```bash
# 完整检查开发环境
flutter doctor -v

# 预期输出类似：
# [✓] Flutter (Channel stable, 3.x.x)
# [✗] Android toolchain (可忽略，我们只需iOS)
# [!] Xcode - develop for iOS and macOS
# [!] CocoaPods not installed
```

---

## 🥥 第三步：安装CocoaPods

由于你的Ruby版本较旧（2.6.10），推荐使用Homebrew安装CocoaPods：

### 方式A：使用Homebrew（推荐，最简单）

```bash
# 1. 使用Homebrew安装
brew install cocoapods

# 2. 验证安装
pod --version

# 预期输出：
# 1.15.x 或更高版本
```

### 方式B：升级Ruby后使用gem安装

```bash
# 1. 使用Homebrew安装新版Ruby
brew install ruby

# 2. 添加新Ruby到PATH
echo 'export PATH="/opt/homebrew/opt/ruby/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 3. 验证Ruby版本
ruby -v
# 应该显示3.x.x

# 4. 安装CocoaPods
gem install cocoapods

# 5. 验证安装
pod --version
```

### 方式C：继续使用旧Ruby（不推荐，可能有兼容性问题）

```bash
# 1. 安装兼容版本的依赖
gem install securerandom -v 0.3.2 --user-install

# 2. 安装CocoaPods（降级版本）
gem install cocoapods -v 1.11.3 --user-install

# 3. 添加gem bin目录到PATH
echo 'export PATH="$HOME/.gem/ruby/2.6.0/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 4. 验证安装
pod --version
```

---

## ✅ 第四步：验证完整环境

运行以下命令确认所有工具已安装：

```bash
# 检查Flutter
flutter --version
flutter doctor

# 检查CocoaPods
pod --version

# 检查Xcode（如果已安装完整版）
xcodebuild -version

# 检查Ruby
ruby -v
```

**预期结果：**
```
✓ Flutter 3.x.x
✓ CocoaPods 1.x.x
✓ Ruby 2.6.10+ 或 3.x.x
```

---

## 🔧 第五步：配置iOS项目依赖

现在环境已就绪，配置你的项目：

```bash
# 1. 进入项目目录
cd /Users/a1-6/Documents/GJ/编程/ai助理new/ai-assistant-mobile

# 2. 获取Flutter依赖
flutter pub get

# 预期输出：
# Running "flutter pub get" in ai-assistant-mobile...
# Resolving dependencies...
# Got dependencies!

# 3. 进入iOS目录
cd ios

# 4. 安装iOS原生依赖
pod install

# 预期输出：
# Analyzing dependencies
# Downloading dependencies
# Installing webview_flutter_wkwebview (3.9.0)
# Installing connectivity_plus (1.x.x)
# ...
# Pod installation complete!

# 5. 返回项目根目录
cd ..
```

---

## 🎮 第六步：运行测试

### 在iOS模拟器中测试

```bash
# 1. 打开iOS模拟器
open -a Simulator

# 等待模拟器启动（约10-30秒）

# 2. 运行应用
flutter run

# 首次运行需要编译，约5-10分钟
# 后续只需几秒钟（热重载）

# 看到以下输出表示成功：
# Flutter run key commands.
# r Hot reload.
# R Hot restart.
# q Quit.
```

### 在真实iPhone上测试

```bash
# 1. 用USB连接iPhone到Mac

# 2. 在iPhone上信任这台电脑

# 3. 启用开发者模式（iPhone设置 → 隐私与安全 → 开发者模式）

# 4. 查看设备列表
flutter devices

# 5. 运行到iPhone
flutter run -d <你的iPhone设备ID>
```

---

## 🏗️ 第七步：构建发布版本

测试成功后，构建Release版本：

```bash
# 1. 确保在项目根目录
cd /Users/a1-6/Documents/GJ/编程/ai助理new/ai-assistant-mobile

# 2. 构建iOS Release版本
flutter build ios --release

# 构建时间：10-20分钟（首次）
# 输出位置：build/ios/iphoneos/Runner.app

# 看到以下输出表示成功：
# ✓ Built build/ios/iphoneos/Runner.app
```

---

## 📱 第八步：使用Xcode打包（可选）

如果需要发布到App Store或创建IPA文件：

```bash
# 1. 打开Xcode项目
open ios/Runner.xcworkspace

# 2. 在Xcode中：
#    - 选择 Runner → Signing & Capabilities
#    - 配置Team和Bundle Identifier
#    - Product → Archive
#    - Distribute App
```

---

## ❓ 常见问题解决

### Q1: Flutter克隆太慢或失败？

**方案1：使用国内镜像**
```bash
export PUB_HOSTED_URL=https://pub.flutter-io.cn
export FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn

git clone https://gitclone.com/github.com/flutter/flutter.git -b stable
```

**方案2：下载压缩包**
访问 https://flutter.cn/docs/get-started/install/macos

### Q2: CocoaPods安装失败？

**解决方案：**
```bash
# 清理gem缓存
gem cleanup

# 使用Homebrew替代
brew install cocoapods
```

### Q3: flutter pub get报错？

**解决方案：**
```bash
# 清理Flutter缓存
flutter clean

# 删除锁文件
rm pubspec.lock

# 重新获取依赖
flutter pub get
```

### Q4: pod install失败？

**解决方案：**
```bash
cd ios

# 清理Pods
rm -rf Pods
rm Podfile.lock

# 更新CocoaPods仓库
pod repo update

# 重新安装
pod install --verbose

cd ..
```

### Q5: Xcode签名错误？

**解决方案：**
1. 打开 Xcode → Preferences → Accounts
2. 添加你的Apple ID
3. 在项目设置中选择Team
4. 修改Bundle Identifier为唯一值

### Q6: 没有完整Xcode，只有命令行工具？

**解决方案：**
```bash
# 从App Store安装完整Xcode
# 然后设置路径：
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
sudo xcodebuild -license accept
sudo xcodebuild -runFirstLaunch
```

---

## 🧹 清理和重置（如果需要）

如果安装出现问题，可以完全清理重来：

```bash
# 清理Flutter
rm -rf ~/flutter

# 清理CocoaPods缓存
rm -rf ~/.cocoapods
pod cache clean --all

# 清理项目依赖
cd /Users/a1-6/Documents/GJ/编程/ai助理new/ai-assistant-mobile
flutter clean
cd ios
rm -rf Pods Podfile.lock
cd ..

# 然后重新开始安装流程
```

---

## 📊 安装进度检查表

在安装过程中，使用此检查表确认每一步：

- [ ] **Flutter SDK**
  - [ ] 克隆或下载完成
  - [ ] 添加到PATH
  - [ ] `flutter --version` 工作
  - [ ] `flutter doctor` 显示Flutter已安装

- [ ] **CocoaPods**
  - [ ] 使用Homebrew或gem安装
  - [ ] `pod --version` 显示版本号
  - [ ] 可以运行`pod repo update`

- [ ] **项目配置**
  - [ ] `flutter pub get` 成功
  - [ ] `pod install` 成功
  - [ ] ios/Pods目录已创建

- [ ] **测试运行**
  - [ ] 模拟器可以打开
  - [ ] `flutter run` 成功
  - [ ] APP显示云服务器界面
  - [ ] 功能正常使用

- [ ] **构建发布**
  - [ ] `flutter build ios --release` 成功
  - [ ] build/ios/iphoneos/Runner.app 已生成

---

## 🚀 快速命令参考

**安装Flutter：**
```bash
cd ~ && git clone https://github.com/flutter/flutter.git -b stable
echo 'export PATH="$HOME/flutter/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
flutter doctor
```

**安装CocoaPods：**
```bash
brew install cocoapods
pod --version
```

**配置项目：**
```bash
cd /Users/a1-6/Documents/GJ/编程/ai助理new/ai-assistant-mobile
flutter pub get
cd ios && pod install && cd ..
```

**运行测试：**
```bash
open -a Simulator
flutter run
```

**构建发布：**
```bash
flutter build ios --release
```

---

## 📞 需要帮助？

如果在安装过程中遇到问题：

1. **查看详细指南**: `IOS_APP_BUILD_GUIDE.md`
2. **运行诊断**: `flutter doctor -v`
3. **查看日志**: `flutter run --verbose`
4. **清理重试**: `flutter clean && flutter pub get`

---

## ⏱️ 下一步操作

完成安装后，请通知我继续帮你：

1. ✅ 测试应用运行
2. ✅ 修复可能的问题
3. ✅ 构建Release版本
4. ✅ 准备App Store发布

---

**祝安装顺利！完成后告诉我进展，我会继续协助你完成iOS APP打包。** 🎉

---

*生成时间: 2025-12-23 23:00 (北京时间)*
