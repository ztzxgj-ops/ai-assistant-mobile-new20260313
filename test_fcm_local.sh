#!/bin/bash
# FCM推送功能本地测试脚本

# set -e  # 注释掉，让脚本继续运行即使有错误

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================="
echo "  FCM推送功能本地测试"
echo "========================================="
echo ""

# 测试计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试函数
test_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
}

test_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
}

test_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

test_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo "📋 测试1: 检查必要文件是否存在"
echo "-----------------------------------"

# 检查Python文件
if [ -f "fcm_push_service.py" ]; then
    test_pass "fcm_push_service.py 存在"
else
    test_fail "fcm_push_service.py 不存在"
fi

if [ -f "mysql_manager.py" ]; then
    test_pass "mysql_manager.py 存在"
else
    test_fail "mysql_manager.py 不存在"
fi

if [ -f "reminder_scheduler.py" ]; then
    test_pass "reminder_scheduler.py 存在"
else
    test_fail "reminder_scheduler.py 不存在"
fi

if [ -f "assistant_web.py" ]; then
    test_pass "assistant_web.py 存在"
else
    test_fail "assistant_web.py 不存在"
fi

# 检查SQL文件
if [ -f "database_device_tokens.sql" ]; then
    test_pass "database_device_tokens.sql 存在"
else
    test_fail "database_device_tokens.sql 不存在"
fi

# 检查Flutter文件
if [ -f "ai-assistant-mobile/lib/services/firebase_messaging_service.dart" ]; then
    test_pass "firebase_messaging_service.dart 存在"
else
    test_fail "firebase_messaging_service.dart 不存在"
fi

# 检查文档文件
if [ -f "FIREBASE_PUSH_SETUP_GUIDE.md" ]; then
    test_pass "FIREBASE_PUSH_SETUP_GUIDE.md 存在"
else
    test_fail "FIREBASE_PUSH_SETUP_GUIDE.md 不存在"
fi

if [ -f "FCM_PUSH_TEST_GUIDE.md" ]; then
    test_pass "FCM_PUSH_TEST_GUIDE.md 存在"
else
    test_fail "FCM_PUSH_TEST_GUIDE.md 不存在"
fi

if [ -f "CONFIGURATION_CHECKLIST.md" ]; then
    test_pass "CONFIGURATION_CHECKLIST.md 存在"
else
    test_fail "CONFIGURATION_CHECKLIST.md 不存在"
fi

echo ""
echo "📋 测试2: Python语法检查"
echo "-----------------------------------"

# 检查Python语法
if python3 -m py_compile fcm_push_service.py 2>/dev/null; then
    test_pass "fcm_push_service.py 语法正确"
else
    test_fail "fcm_push_service.py 语法错误"
fi

if python3 -m py_compile mysql_manager.py 2>/dev/null; then
    test_pass "mysql_manager.py 语法正确"
else
    test_fail "mysql_manager.py 语法错误"
fi

if python3 -m py_compile reminder_scheduler.py 2>/dev/null; then
    test_pass "reminder_scheduler.py 语法正确"
else
    test_fail "reminder_scheduler.py 语法错误"
fi

if python3 -m py_compile assistant_web.py 2>/dev/null; then
    test_pass "assistant_web.py 语法正确"
else
    test_fail "assistant_web.py 语法错误"
fi

echo ""
echo "📋 测试3: Python模块导入测试"
echo "-----------------------------------"

# 测试fcm_push_service导入
if python3 -c "from fcm_push_service import FCMPushService, get_fcm_service" 2>/dev/null; then
    test_pass "fcm_push_service 模块导入成功"
else
    test_warn "fcm_push_service 模块导入失败（可能缺少firebase-admin）"
fi

# 测试DeviceTokenManager导入
if python3 -c "from mysql_manager import DeviceTokenManager" 2>/dev/null; then
    test_pass "DeviceTokenManager 导入成功"
else
    test_fail "DeviceTokenManager 导入失败"
fi

echo ""
echo "📋 测试4: 检查Python依赖"
echo "-----------------------------------"

# 检查firebase-admin
if python3 -c "import firebase_admin" 2>/dev/null; then
    test_pass "firebase-admin 已安装"
    FIREBASE_VERSION=$(python3 -c "import firebase_admin; print(firebase_admin.__version__)" 2>/dev/null)
    test_info "版本: $FIREBASE_VERSION"
else
    test_warn "firebase-admin 未安装（需要运行: pip3 install firebase-admin）"
fi

echo ""
echo "📋 测试5: 数据库SQL语法检查"
echo "-----------------------------------"

# 检查SQL文件语法（简单检查）
if grep -q "CREATE TABLE IF NOT EXISTS device_tokens" database_device_tokens.sql; then
    test_pass "SQL文件包含CREATE TABLE语句"
else
    test_fail "SQL文件格式错误"
fi

if grep -q "FOREIGN KEY (user_id) REFERENCES users(id)" database_device_tokens.sql; then
    test_pass "SQL文件包含外键约束"
else
    test_fail "SQL文件缺少外键约束"
fi

echo ""
echo "📋 测试6: Flutter依赖检查"
echo "-----------------------------------"

cd ai-assistant-mobile

# 检查pubspec.yaml
if grep -q "firebase_core:" pubspec.yaml; then
    test_pass "pubspec.yaml 包含 firebase_core"
else
    test_fail "pubspec.yaml 缺少 firebase_core"
fi

if grep -q "firebase_messaging:" pubspec.yaml; then
    test_pass "pubspec.yaml 包含 firebase_messaging"
else
    test_fail "pubspec.yaml 缺少 firebase_messaging"
fi

# 检查是否已安装
if [ -f "pubspec.lock" ]; then
    if grep -q "firebase_core:" pubspec.lock; then
        test_pass "firebase_core 已安装"
        CORE_VERSION=$(grep -A 1 "firebase_core:" pubspec.lock | grep "version:" | awk '{print $2}' | tr -d '"')
        test_info "版本: $CORE_VERSION"
    else
        test_warn "firebase_core 未安装"
    fi

    if grep -q "firebase_messaging:" pubspec.lock; then
        test_pass "firebase_messaging 已安装"
        MSG_VERSION=$(grep -A 1 "firebase_messaging:" pubspec.lock | grep "version:" | awk '{print $2}' | tr -d '"')
        test_info "版本: $MSG_VERSION"
    else
        test_warn "firebase_messaging 未安装"
    fi
fi

cd ..

echo ""
echo "📋 测试7: 检查配置文件"
echo "-----------------------------------"

# 检查firebase_config.json
if [ -f "firebase_config.json" ]; then
    test_pass "firebase_config.json 存在"
    if grep -q "project_id" firebase_config.json; then
        test_pass "firebase_config.json 包含 project_id"
    else
        test_fail "firebase_config.json 格式错误"
    fi
else
    test_warn "firebase_config.json 不存在（需要从Firebase控制台下载）"
fi

# 检查示例文件
if [ -f "firebase_config.json.example" ]; then
    test_pass "firebase_config.json.example 存在"
else
    test_warn "firebase_config.json.example 不存在"
fi

echo ""
echo "📋 测试8: 检查部署脚本"
echo "-----------------------------------"

if [ -f "deploy_fcm_push.sh" ]; then
    test_pass "deploy_fcm_push.sh 存在"
    if [ -x "deploy_fcm_push.sh" ]; then
        test_pass "deploy_fcm_push.sh 可执行"
    else
        test_warn "deploy_fcm_push.sh 不可执行（运行: chmod +x deploy_fcm_push.sh）"
    fi
else
    test_fail "deploy_fcm_push.sh 不存在"
fi

echo ""
echo "========================================="
echo "  测试结果汇总"
echo "========================================="
echo ""
echo -e "总测试数: ${BLUE}$TOTAL_TESTS${NC}"
echo -e "通过: ${GREEN}$PASSED_TESTS${NC}"
echo -e "失败: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有测试通过！${NC}"
    echo ""
    echo "📝 下一步："
    echo "  1. 从Firebase控制台下载配置文件"
    echo "  2. 配置iOS和Android应用"
    echo "  3. 运行部署脚本: ./deploy_fcm_push.sh"
    echo "  4. 在真机上测试推送功能"
    echo ""
    exit 0
else
    echo -e "${RED}❌ 有 $FAILED_TESTS 个测试失败${NC}"
    echo ""
    echo "请检查失败的测试项并修复问题"
    echo ""
    exit 1
fi
