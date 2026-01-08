#!/bin/bash
# 配置国内镜像
export PUB_HOSTED_URL=https://pub.flutter-io.cn
export FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn
export PATH="$PATH:$HOME/development/flutter/bin:$HOME/.gem/ruby/2.6.0/bin"

echo "=== 1. 尝试使用国内镜像修复 Flutter ==="
flutter doctor

echo "=== 2. 再次尝试修复 Ruby 依赖 (极简模式) ==="
# 尝试安装更旧的版本以求兼容
gem install zeitwerk -v 2.6.0 --user-install --no-document
gem install connection_pool -v 2.2.5 --user-install --no-document
gem install activesupport -v 6.0.0 --user-install --no-document
gem install cocoapods -v 1.10.0 --user-install --no-document

echo "=== 3. 检查结果 ==="
if command -v pod &> /dev/null; then
    echo "✅ CocoaPods 安装成功！"
else
    echo "⚠️ CocoaPods 依然失败，建议升级 macOS 或安装 Homebrew (brew.sh)"
fi

echo "=== 4. 提醒 ==="
echo "请务必在 App Store 中完成 Xcode 的下载和安装！"
echo "安装完成后，运行: sudo xcode-select --switch /Applications/Xcode.app"
