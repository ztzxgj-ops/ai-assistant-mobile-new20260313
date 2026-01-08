#!/bin/bash
export PATH="$PATH:$HOME/development/flutter/bin"
export PATH="$PATH:$HOME/.gem/ruby/2.6.0/bin"

echo "=== 修复 Ruby 依赖 ==="
# 强制安装旧版本依赖以兼容 MacOS 自带的 Ruby 2.6
gem install securerandom -v 0.3.2 --user-install --no-document
gem install drb -v 2.0.5 --user-install --no-document
gem install activesupport -v 6.1.7.6 --user-install --no-document
gem install cocoapods-core -v 1.12.1 --user-install --no-document
gem install cocoapods-downloader -v 1.6.3 --user-install --no-document

echo "=== 安装 CocoaPods 1.12.1 ==="
gem install cocoapods -v 1.12.1 --user-install --no-document

echo "=== 检查环境 ==="
flutter doctor

echo "=== 处理 Xcode ==="
if [ -d "/Applications/Xcode.app" ]; then
    echo "✅ Xcode 已安装"
else
    echo "正在打开 App Store 下载 Xcode..."
    open "macappstore://itunes.apple.com/app/id497799835"
fi
