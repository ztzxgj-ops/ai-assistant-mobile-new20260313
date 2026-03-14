#!/bin/bash

################################################################################
# macOS Electron 应用快速命令脚本
# 提供常用的快捷命令
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_SCRIPT="${SCRIPT_DIR}/build-macos.sh"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ============================================================================
# 快速命令
# ============================================================================

# 快速构建
quick_build() {
    print_header "快速构建..."
    "$BUILD_SCRIPT"
}

# 完整构建
full_build() {
    print_header "完整构建（清理 + 安装 + 构建 + 签名）..."
    "$BUILD_SCRIPT" --all --sign
}

# 构建并上传
build_and_upload() {
    print_header "构建并上传到服务器..."
    "$BUILD_SCRIPT" --all --upload
}

# 仅清理
clean_only() {
    print_header "清理构建文件..."
    "$BUILD_SCRIPT" --clean
}

# 仅安装依赖
install_only() {
    print_header "安装依赖..."
    "$BUILD_SCRIPT" --install
}

# 测试应用
test_app() {
    print_header "启动应用..."

    local app_path="${SCRIPT_DIR}/dist/AI个人助理.app"

    if [ ! -d "$app_path" ]; then
        print_warning "应用未找到，请先构建"
        return 1
    fi

    open "$app_path"
    print_success "应用已启动"
}

# 查看构建日志
view_logs() {
    print_header "查看最新构建日志..."

    local latest_log=$(ls -t "${SCRIPT_DIR}/build-output/build-"*.log 2>/dev/null | head -1)

    if [ -z "$latest_log" ]; then
        print_warning "未找到构建日志"
        return 1
    fi

    tail -f "$latest_log"
}

# 查看构建报告
view_report() {
    print_header "查看最新构建报告..."

    local latest_report=$(ls -t "${SCRIPT_DIR}/build-output/build-report-"*.md 2>/dev/null | head -1)

    if [ -z "$latest_report" ]; then
        print_warning "未找到构建报告"
        return 1
    fi

    cat "$latest_report"
}

# 验证应用签名
verify_signature() {
    print_header "验证应用签名..."

    local app_path="${SCRIPT_DIR}/dist/AI个人助理.app"

    if [ ! -d "$app_path" ]; then
        print_warning "应用未找到"
        return 1
    fi

    if codesign -v "$app_path"; then
        print_success "签名验证通过"
    else
        print_warning "签名验证失败"
        return 1
    fi
}

# 显示应用信息
show_app_info() {
    print_header "应用信息..."

    local app_path="${SCRIPT_DIR}/dist/AI个人助理.app"

    if [ ! -d "$app_path" ]; then
        print_warning "应用未找到"
        return 1
    fi

    mdls "$app_path"
}

# 打开应用目录
open_dist_dir() {
    print_header "打开应用目录..."

    local dist_dir="${SCRIPT_DIR}/dist"

    if [ ! -d "$dist_dir" ]; then
        print_warning "dist 目录不存在"
        return 1
    fi

    open "$dist_dir"
    print_success "已打开 dist 目录"
}

# 打开构建输出目录
open_output_dir() {
    print_header "打开构建输出目录..."

    local output_dir="${SCRIPT_DIR}/build-output"

    mkdir -p "$output_dir"
    open "$output_dir"
    print_success "已打开 build-output 目录"
}

# 清理所有构建文件
clean_all() {
    print_header "清理所有构建文件..."

    read -p "确定要删除 dist 和 node_modules 目录吗？(y/n) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "${SCRIPT_DIR}/dist"
        rm -rf "${SCRIPT_DIR}/node_modules"
        print_success "已清理所有构建文件"
    else
        print_warning "已取消"
    fi
}

# 显示帮助
show_help() {
    cat << EOF
macOS Electron 应用快速命令

使用方法: ./quick-build.sh <命令>

命令列表:
    build               快速构建应用
    full                完整构建（清理 + 安装 + 构建 + 签名）
    upload              构建并上传到服务器
    clean               清理构建文件
    install             安装依赖
    test                启动应用进行测试
    logs                查看最新构建日志
    report              查看最新构建报告
    verify              验证应用签名
    info                显示应用信息
    open-dist           打开 dist 目录
    open-output         打开 build-output 目录
    clean-all           清理所有构建文件
    help                显示此帮助信息

快速命令示例:
    ./quick-build.sh build              # 快速构建
    ./quick-build.sh full               # 完整构建
    ./quick-build.sh upload             # 构建并上传
    ./quick-build.sh test               # 测试应用
    ./quick-build.sh logs               # 查看日志

EOF
}

# ============================================================================
# 主程序
# ============================================================================

main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    case "$1" in
        build)
            quick_build
            ;;
        full)
            full_build
            ;;
        upload)
            build_and_upload
            ;;
        clean)
            clean_only
            ;;
        install)
            install_only
            ;;
        test)
            test_app
            ;;
        logs)
            view_logs
            ;;
        report)
            view_report
            ;;
        verify)
            verify_signature
            ;;
        info)
            show_app_info
            ;;
        open-dist)
            open_dist_dir
            ;;
        open-output)
            open_output_dir
            ;;
        clean-all)
            clean_all
            ;;
        help)
            show_help
            ;;
        *)
            echo "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
