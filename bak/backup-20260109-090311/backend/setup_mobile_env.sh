#!/bin/bash
#############################################
# AI助理 - 移动端环境强制配置脚本
#############################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FLUTTER_DIR="$HOME/development/flutter"

echo -e "${BLUE}=========================================="
echo "   AI助理 - 移动端环境强制配置"
echo "==========================================${NC}"
echo ""

# 1. 安装/检查Flutter (优先执行)
echo -e "${YELLOW}[1/4] 检查Flutter环境...${NC}"

if command -v flutter &> /dev/null; then
    echo -e "${GREEN}✅ Flutter已安装: $(flutter --version | head -1)${NC}"
else
    echo "未检测到Flutter，正在安装..."
    mkdir -p ~/development
    
    if [ ! -d "$FLUTTER_DIR" ]; then
        echo "正在下载Flutter SDK..."
        git clone https://github.com/flutter/flutter.git -b stable "$FLUTTER_DIR"
    fi
    
    # 配置环境变量
    SHELL_CONFIG="$HOME/.zshrc"
    if [[ "$SHELL" == *"bash"* ]]; then
        SHELL_CONFIG="$HOME/.bash_profile"
    fi
    
    if ! grep -q "flutter/bin" "$SHELL_CONFIG"; then
        echo >> "$SHELL_CONFIG"
        echo '# Flutter Path' >> "$SHELL_CONFIG"
        echo "export PATH=\"
$PATH:$FLUTTER_DIR/bin\"" >> "$SHELL_CONFIG"
    fi
    
    export PATH="$PATH:$FLUTTER_DIR/bin"
    echo -e "${GREEN}✅ Flutter安装完成${NC}"
fi

# 2. 安装CocoaPods
echo ""
echo -e "${YELLOW}[2/4] 检查CocoaPods...${NC}"
if command -v pod &> /dev/null; then
    echo -e "${GREEN}✅ CocoaPods已安装${NC}"
else
    echo "正在安装CocoaPods..."
    # 尝试无需sudo安装
    gem install cocoapods --user-install
    
    # 检查是否成功，如果失败提示需要sudo
    if ! command -v pod &> /dev/null; then
        echo -e "${YELLOW}普通用户安装失败，尝试sudo安装 (可能需要密码)${NC}"
        sudo gem install cocoapods
    fi
    echo -e "${GREEN}✅ CocoaPods安装完成${NC}"
fi

# 3. 初始化项目 (无论Xcode是否存在都先下载依赖)
echo ""
echo -e "${YELLOW}[3/4] 初始化项目依赖...${NC}"
PROJECT_DIR="$(pwd)/ai-assistant-mobile"

if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR"
    echo "获取Flutter依赖..."
    flutter pub get
else
    echo "找不到项目目录，跳过初始化"
fi

# 4. 处理Xcode (最难的部分)
echo ""
echo -e "${YELLOW}[4/4] 处理Xcode安装...${NC}"

if [ -d "/Applications/Xcode.app" ]; then
    echo -e "${GREEN}✅ Xcode已安装${NC}"
    sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
else
    echo "❌ 未检测到Xcode应用"
    echo "尝试自动安装..."
    
    # 检查是否有mas (Mac App Store CLI)
    if command -v mas &> /dev/null; then
        echo "检测到mas工具，尝试命令行安装Xcode..."
        mas install 497799835
    else
        echo "未检测到mas工具，正在唤起App Store下载页面..."
        # 直接打开App Store的Xcode页面
        open "macappstore://itunes.apple.com/app/id497799835"
        echo "⚠️  App Store已打开"
        echo "⚠️  请在弹出的窗口中点击【获取】或【下载】按钮"
    fi
fi

echo ""
echo -e "${BLUE}=========================================="
echo "   配置脚本执行完毕"
echo "==========================================${NC}"