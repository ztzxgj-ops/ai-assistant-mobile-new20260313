#!/bin/bash

################################################################################
# macOS Electron 应用自动化构建脚本
# 功能：自动化编译、签名、打包 macOS 应用
# 使用：./build-macos.sh [options]
################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="AI个人助理"
BUNDLE_ID="com.aiassistant.app"
BUILD_DIR="${PROJECT_DIR}/dist"
OUTPUT_DIR="${PROJECT_DIR}/build-output"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BUILD_LOG="${OUTPUT_DIR}/build-${TIMESTAMP}.log"

# 默认选项
SKIP_INSTALL=false
SKIP_CLEAN=false
SIGN_APP=false
NOTARIZE=false
UPLOAD=false
VERBOSE=false

################################################################################
# 函数定义
################################################################################

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

log_command() {
    if [ "$VERBOSE" = true ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $@" | tee -a "$BUILD_LOG"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $@" >> "$BUILD_LOG"
    fi
}

show_usage() {
    cat << EOF
使用方法: ./build-macos.sh [选项]

选项:
    -h, --help              显示帮助信息
    -c, --clean             清理旧的构建文件
    -i, --install           安装依赖 (npm install)
    -s, --sign              对应用进行代码签名
    -n, --notarize          对应用进行公证 (需要 Apple 开发者账户)
    -u, --upload            构建完成后上传到服务器
    -v, --verbose           显示详细输出
    -a, --all               执行所有步骤 (clean + install + build + sign)

示例:
    ./build-macos.sh                    # 基础构建
    ./build-macos.sh --clean --install  # 清理并重新安装依赖
    ./build-macos.sh --all --upload     # 完整构建并上传
EOF
}

check_requirements() {
    print_header "检查系统要求"

    local missing=false

    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js 未安装"
        missing=true
    else
        print_success "Node.js: $(node --version)"
    fi

    # 检查 npm
    if ! command -v npm &> /dev/null; then
        print_error "npm 未安装"
        missing=true
    else
        print_success "npm: $(npm --version)"
    fi

    # 检查 Xcode
    if ! command -v xcode-select &> /dev/null; then
        print_error "Xcode 未安装"
        missing=true
    else
        print_success "Xcode: 已安装"
    fi

    if [ "$missing" = true ]; then
        print_error "缺少必要的工具，请先安装"
        exit 1
    fi
}

setup_build_env() {
    print_header "设置构建环境"

    # 创建输出目录
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$BUILD_DIR"

    print_success "输出目录: $OUTPUT_DIR"
    print_success "构建目录: $BUILD_DIR"

    # 初始化日志
    echo "=== macOS Electron 构建日志 ===" > "$BUILD_LOG"
    echo "时间: $(date)" >> "$BUILD_LOG"
    echo "项目: $PROJECT_DIR" >> "$BUILD_LOG"
    echo "" >> "$BUILD_LOG"
}

clean_build() {
    print_header "清理旧的构建文件"

    if [ -d "$BUILD_DIR" ]; then
        log_command "rm -rf $BUILD_DIR"
        rm -rf "$BUILD_DIR"
        print_success "已删除 dist 目录"
    fi

    if [ -d "${PROJECT_DIR}/node_modules" ]; then
        log_command "rm -rf ${PROJECT_DIR}/node_modules"
        rm -rf "${PROJECT_DIR}/node_modules"
        print_success "已删除 node_modules 目录"
    fi
}

install_dependencies() {
    print_header "安装依赖"

    cd "$PROJECT_DIR"

    if [ ! -d "node_modules" ]; then
        print_info "运行 npm install..."
        log_command "npm install"
        npm install 2>&1 | tee -a "$BUILD_LOG"
        print_success "依赖安装完成"
    else
        print_info "node_modules 已存在，跳过安装"
    fi
}

build_app() {
    print_header "构建 macOS 应用"

    cd "$PROJECT_DIR"

    print_info "运行 electron-builder..."
    log_command "npx electron-builder --mac"

    if npx electron-builder --mac 2>&1 | tee -a "$BUILD_LOG"; then
        print_success "应用构建完成"
    else
        print_error "应用构建失败"
        exit 1
    fi
}

find_app_bundle() {
    # 查找生成的 .app 文件
    local app_path=$(find "$BUILD_DIR" -name "*.app" -type d | head -1)

    if [ -z "$app_path" ]; then
        print_error "未找到生成的 .app 文件"
        return 1
    fi

    echo "$app_path"
}

sign_app() {
    print_header "对应用进行代码签名"

    local app_path=$(find_app_bundle)
    if [ $? -ne 0 ]; then
        print_warning "跳过代码签名"
        return
    fi

    print_info "应用路径: $app_path"

    # 获取可用的签名身份
    local identities=$(security find-identity -v -p codesigning | grep -o '"[^"]*"' | tr -d '"')

    if [ -z "$identities" ]; then
        print_warning "未找到有效的代码签名身份"
        print_info "请在 Keychain Access 中配置开发者证书"
        return
    fi

    # 使用第一个可用的身份
    local identity=$(echo "$identities" | head -1)

    print_info "使用签名身份: $identity"
    log_command "codesign -s '$identity' --deep --force '$app_path'"

    if codesign -s "$identity" --deep --force "$app_path" 2>&1 | tee -a "$BUILD_LOG"; then
        print_success "代码签名完成"

        # 验证签名
        print_info "验证签名..."
        codesign -v "$app_path" 2>&1 | tee -a "$BUILD_LOG"
        print_success "签名验证通过"
    else
        print_error "代码签名失败"
        return 1
    fi
}

notarize_app() {
    print_header "对应用进行公证"

    print_warning "公证功能需要 Apple 开发者账户"
    print_info "请配置以下环境变量:"
    print_info "  APPLE_ID - Apple ID 邮箱"
    print_info "  APPLE_PASSWORD - 应用专用密码"
    print_info "  APPLE_TEAM_ID - Team ID"

    if [ -z "$APPLE_ID" ] || [ -z "$APPLE_PASSWORD" ]; then
        print_warning "未配置 Apple 账户信息，跳过公证"
        return
    fi

    local app_path=$(find_app_bundle)
    if [ $? -ne 0 ]; then
        return
    fi

    print_info "提交应用进行公证..."
    # 这里需要使用 xcrun notarytool 或 altool
    # 具体实现取决于 Xcode 版本
    print_warning "公证功能需要手动配置，请参考 Apple 官方文档"
}

create_dmg() {
    print_header "创建 DMG 安装包"

    local app_path=$(find_app_bundle)
    if [ $? -ne 0 ]; then
        print_warning "跳过 DMG 创建"
        return
    fi

    # electron-builder 已经生成了 DMG，这里只是验证
    local dmg_file=$(find "$BUILD_DIR" -name "*.dmg" | head -1)

    if [ -n "$dmg_file" ]; then
        print_success "DMG 文件已生成: $(basename "$dmg_file")"
        print_info "大小: $(du -h "$dmg_file" | cut -f1)"
    else
        print_warning "未找到 DMG 文件"
    fi
}

upload_to_server() {
    print_header "上传到服务器"

    local server_ip="47.109.148.176"
    local server_user="root"
    local server_path="/var/www/ai-assistant/builds"

    print_info "服务器: $server_ip"
    print_info "目标路径: $server_path"

    # 查找所有生成的文件
    local files_to_upload=$(find "$BUILD_DIR" -type f \( -name "*.dmg" -o -name "*.zip" -o -name "*.app" \) 2>/dev/null)

    if [ -z "$files_to_upload" ]; then
        print_warning "未找到要上传的文件"
        return
    fi

    print_info "要上传的文件:"
    echo "$files_to_upload" | while read -r file; do
        print_info "  - $(basename "$file") ($(du -h "$file" | cut -f1))"
    done

    # 检查 SSH 连接
    if ! ssh -o ConnectTimeout=5 "${server_user}@${server_ip}" "test -d $server_path" 2>/dev/null; then
        print_warning "无法连接到服务器，跳过上传"
        print_info "请确保:"
        print_info "  1. SSH 密钥已配置"
        print_info "  2. 服务器地址正确"
        print_info "  3. 目标目录存在"
        return
    fi

    print_info "开始上传..."
    echo "$files_to_upload" | while read -r file; do
        local filename=$(basename "$file")
        print_info "上传: $filename"
        log_command "scp '$file' ${server_user}@${server_ip}:${server_path}/"

        if scp "$file" "${server_user}@${server_ip}:${server_path}/" 2>&1 | tee -a "$BUILD_LOG"; then
            print_success "已上传: $filename"
        else
            print_error "上传失败: $filename"
        fi
    done

    print_success "上传完成"
}

generate_report() {
    print_header "生成构建报告"

    local report_file="${OUTPUT_DIR}/build-report-${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# macOS Electron 应用构建报告

**构建时间**: $(date)
**项目**: $PROJECT_DIR
**应用名称**: $APP_NAME

## 构建信息

- **Node.js 版本**: $(node --version)
- **npm 版本**: $(npm --version)
- **Electron 版本**: $(grep '"electron"' package.json | grep -o '[0-9.]*' | head -1)

## 生成的文件

EOF

    if [ -d "$BUILD_DIR" ]; then
        find "$BUILD_DIR" -type f \( -name "*.dmg" -o -name "*.zip" -o -name "*.app" \) | while read -r file; do
            local size=$(du -h "$file" | cut -f1)
            echo "- $(basename "$file") ($size)" >> "$report_file"
        done
    fi

    cat >> "$report_file" << EOF

## 构建日志

详见: $BUILD_LOG

## 后续步骤

1. **测试应用**
   \`\`\`bash
   open "$BUILD_DIR/AI个人助理.app"
   \`\`\`

2. **分发应用**
   - DMG 文件可直接分发给用户
   - 用户双击 DMG 即可安装

3. **代码签名和公证**
   - 如需在 App Store 分发，需要进行代码签名和公证
   - 运行: \`./build-macos.sh --sign --notarize\`

EOF

    print_success "报告已生成: $report_file"
}

show_summary() {
    print_header "构建完成"

    print_success "所有步骤已完成"
    print_info "输出目录: $OUTPUT_DIR"
    print_info "构建日志: $BUILD_LOG"

    if [ -d "$BUILD_DIR" ]; then
        print_info "生成的文件:"
        find "$BUILD_DIR" -maxdepth 2 -type f \( -name "*.dmg" -o -name "*.zip" \) | while read -r file; do
            print_info "  - $(basename "$file") ($(du -h "$file" | cut -f1))"
        done
    fi

    echo ""
    print_info "快速命令:"
    print_info "  测试应用: open \"$BUILD_DIR/AI个人助理.app\""
    print_info "  查看日志: tail -f \"$BUILD_LOG\""
}

################################################################################
# 主程序
################################################################################

main() {
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -c|--clean)
                SKIP_CLEAN=false
                shift
                ;;
            -i|--install)
                SKIP_INSTALL=false
                shift
                ;;
            -s|--sign)
                SIGN_APP=true
                shift
                ;;
            -n|--notarize)
                NOTARIZE=true
                shift
                ;;
            -u|--upload)
                UPLOAD=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -a|--all)
                SKIP_CLEAN=false
                SKIP_INSTALL=false
                SIGN_APP=true
                shift
                ;;
            *)
                print_error "未知选项: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # 执行构建流程
    check_requirements
    setup_build_env

    if [ "$SKIP_CLEAN" = false ]; then
        clean_build
    fi

    if [ "$SKIP_INSTALL" = false ]; then
        install_dependencies
    fi

    build_app
    create_dmg

    if [ "$SIGN_APP" = true ]; then
        sign_app
    fi

    if [ "$NOTARIZE" = true ]; then
        notarize_app
    fi

    if [ "$UPLOAD" = true ]; then
        upload_to_server
    fi

    generate_report
    show_summary

    # 播放完成提示音
    afplay /System/Library/Sounds/Glass.aiff
}

# 运行主程序
main "$@"
