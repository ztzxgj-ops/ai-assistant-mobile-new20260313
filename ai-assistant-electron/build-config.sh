#!/bin/bash

################################################################################
# macOS Electron 应用高级构建配置
# 用于自定义构建参数和优化选项
################################################################################

# ============================================================================
# 应用信息配置
# ============================================================================

# 应用名称
export APP_NAME="AI个人助理"

# Bundle ID（用于代码签名和 App Store）
export BUNDLE_ID="com.aiassistant.app"

# 应用版本
export APP_VERSION="1.0.0"

# 应用描述
export APP_DESCRIPTION="AI个人助理 - 桌面版（连接云服务器）"

# ============================================================================
# 构建配置
# ============================================================================

# 构建输出目录
export BUILD_OUTPUT_DIR="dist"

# 临时构建目录
export BUILD_TEMP_DIR=".build-temp"

# 是否生成通用二进制文件（支持 Intel 和 Apple Silicon）
export BUILD_UNIVERSAL=true

# 目标架构（x64, arm64, 或两者）
export TARGET_ARCHS="x64 arm64"

# ============================================================================
# 代码签名配置
# ============================================================================

# 代码签名证书名称（留空则自动检测）
export SIGNING_IDENTITY=""

# 是否启用硬化运行时（Hardened Runtime）
export ENABLE_HARDENED_RUNTIME=true

# 是否禁用 Gatekeeper 评估
export DISABLE_GATEKEEPER=false

# ============================================================================
# 公证配置（Apple Developer Account）
# ============================================================================

# Apple ID 邮箱
export APPLE_ID=""

# 应用专用密码（从 appleid.apple.com 生成）
export APPLE_PASSWORD=""

# Team ID
export APPLE_TEAM_ID=""

# 公证超时时间（秒）
export NOTARIZE_TIMEOUT=3600

# ============================================================================
# 服务器上传配置
# ============================================================================

# 服务器 IP 地址
export SERVER_IP="47.109.148.176"

# 服务器用户名
export SERVER_USER="root"

# 服务器上的目标目录
export SERVER_BUILD_DIR="/var/www/ai-assistant/builds"

# SSH 密钥路径（留空则使用默认 ~/.ssh/id_rsa）
export SSH_KEY_PATH=""

# SSH 端口
export SSH_PORT=22

# 上传后是否删除本地文件
export DELETE_AFTER_UPLOAD=false

# ============================================================================
# 打包配置
# ============================================================================

# 是否生成 DMG 文件
export GENERATE_DMG=true

# 是否生成 ZIP 文件
export GENERATE_ZIP=true

# DMG 窗口宽度
export DMG_WINDOW_WIDTH=600

# DMG 窗口高度
export DMG_WINDOW_HEIGHT=400

# DMG 图标大小
export DMG_ICON_SIZE=100

# ============================================================================
# 性能优化
# ============================================================================

# 并行构建任务数
export PARALLEL_JOBS=4

# 是否启用缓存
export ENABLE_CACHE=true

# 缓存目录
export CACHE_DIR=".build-cache"

# ============================================================================
# 日志配置
# ============================================================================

# 日志级别（debug, info, warn, error）
export LOG_LEVEL="info"

# 日志输出目录
export LOG_DIR="build-output"

# 是否保存详细日志
export SAVE_DETAILED_LOG=true

# 日志文件最大大小（MB）
export LOG_MAX_SIZE=100

# ============================================================================
# 通知配置
# ============================================================================

# 构建完成后是否发送通知
export SEND_NOTIFICATION=true

# 构建失败后是否发送通知
export NOTIFY_ON_FAILURE=true

# 通知方式（system, email, slack）
export NOTIFICATION_METHOD="system"

# Slack Webhook URL（如果使用 Slack 通知）
export SLACK_WEBHOOK_URL=""

# ============================================================================
# 开发配置
# ============================================================================

# 是否启用开发者工具
export ENABLE_DEV_TOOLS=false

# 是否启用调试模式
export DEBUG_MODE=false

# 是否启用热重载
export ENABLE_HOT_RELOAD=false

# ============================================================================
# 高级选项
# ============================================================================

# 自定义 electron-builder 配置文件
export ELECTRON_BUILDER_CONFIG="electron-builder.json"

# 自定义 package.json 路径
export PACKAGE_JSON_PATH="package.json"

# 是否跳过依赖检查
export SKIP_DEPENDENCY_CHECK=false

# 是否跳过系统要求检查
export SKIP_SYSTEM_CHECK=false

# 构建前执行的自定义脚本
export PRE_BUILD_SCRIPT=""

# 构建后执行的自定义脚本
export POST_BUILD_SCRIPT=""

# ============================================================================
# 环境变量导出
# ============================================================================

# 导出所有配置为环境变量
export_config() {
    echo "✓ 构建配置已加载"
    echo "  应用名称: $APP_NAME"
    echo "  版本: $APP_VERSION"
    echo "  Bundle ID: $BUNDLE_ID"
    echo "  目标架构: $TARGET_ARCHS"
    echo "  输出目录: $BUILD_OUTPUT_DIR"
}

# 验证配置
validate_config() {
    local errors=0

    # 检查必要的配置
    if [ -z "$APP_NAME" ]; then
        echo "✗ 错误: APP_NAME 未设置"
        ((errors++))
    fi

    if [ -z "$BUNDLE_ID" ]; then
        echo "✗ 错误: BUNDLE_ID 未设置"
        ((errors++))
    fi

    # 检查服务器配置
    if [ -n "$SERVER_IP" ] && [ -z "$SERVER_USER" ]; then
        echo "✗ 错误: 已设置 SERVER_IP 但未设置 SERVER_USER"
        ((errors++))
    fi

    # 检查公证配置
    if [ -n "$APPLE_ID" ] && [ -z "$APPLE_PASSWORD" ]; then
        echo "✗ 错误: 已设置 APPLE_ID 但未设置 APPLE_PASSWORD"
        ((errors++))
    fi

    if [ $errors -gt 0 ]; then
        echo "✗ 配置验证失败，共 $errors 个错误"
        return 1
    fi

    echo "✓ 配置验证通过"
    return 0
}

# 显示配置摘要
show_config_summary() {
    cat << EOF
╔════════════════════════════════════════════════════════════════╗
║           macOS Electron 应用构建配置摘要                      ║
╚════════════════════════════════════════════════════════════════╝

【应用信息】
  名称: $APP_NAME
  版本: $APP_VERSION
  Bundle ID: $BUNDLE_ID

【构建配置】
  输出目录: $BUILD_OUTPUT_DIR
  目标架构: $TARGET_ARCHS
  通用二进制: $BUILD_UNIVERSAL

【代码签名】
  签名证书: ${SIGNING_IDENTITY:-自动检测}
  硬化运行时: $ENABLE_HARDENED_RUNTIME

【打包配置】
  生成 DMG: $GENERATE_DMG
  生成 ZIP: $GENERATE_ZIP

【服务器配置】
  服务器: ${SERVER_IP:-未配置}
  用户: ${SERVER_USER:-未配置}
  目标目录: ${SERVER_BUILD_DIR:-未配置}

【性能优化】
  并行任务: $PARALLEL_JOBS
  启用缓存: $ENABLE_CACHE

【日志配置】
  日志级别: $LOG_LEVEL
  日志目录: $LOG_DIR

EOF
}

# 如果直接运行此脚本，显示配置摘要
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    export_config
    echo ""
    show_config_summary
    validate_config
fi
