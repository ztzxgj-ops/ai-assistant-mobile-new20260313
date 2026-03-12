#!/bin/bash
# DNS记录检查脚本

echo "=========================================="
echo "🔍 DNS记录检查工具"
echo "=========================================="
echo ""

# 获取域名
read -p "请输入你的邮件域名（例如：mail.assistant230.top）: " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "❌ 域名不能为空"
    exit 1
fi

echo ""
echo "正在检查域名: $DOMAIN"
echo ""

# 检查SPF记录
echo "1️⃣ 检查SPF记录（TXT）..."
echo "----------------------------------------"
SPF_RESULT=$(nslookup -type=txt "$DOMAIN" 2>&1)
if echo "$SPF_RESULT" | grep -q "spf1"; then
    echo "✅ SPF记录已配置"
    echo "$SPF_RESULT" | grep "spf1"
else
    echo "❌ 未找到SPF记录"
    echo "   应该包含: v=spf1 include:spf.mxhichina.com -all"
fi
echo ""

# 检查MX记录
echo "2️⃣ 检查MX记录..."
echo "----------------------------------------"
MX_RESULT=$(nslookup -type=mx "$DOMAIN" 2>&1)
if echo "$MX_RESULT" | grep -q "mxhichina"; then
    echo "✅ MX记录已配置"
    echo "$MX_RESULT" | grep "mail exchanger"
else
    echo "❌ 未找到MX记录"
    echo "   应该指向: mxn.mxhichina.com"
fi
echo ""

# 检查CNAME记录（如果有）
echo "3️⃣ 检查CNAME记录..."
echo "----------------------------------------"
CNAME_RESULT=$(nslookup -type=cname "$DOMAIN" 2>&1)
if echo "$CNAME_RESULT" | grep -q "canonical name"; then
    echo "✅ CNAME记录已配置"
    echo "$CNAME_RESULT" | grep "canonical name"
else
    echo "ℹ️  未找到CNAME记录（可能不需要或使用其他验证方式）"
fi
echo ""

# 总结
echo "=========================================="
echo "📋 检查总结"
echo "=========================================="
echo ""
echo "如果DNS记录未生效："
echo "  1. 检查是否正确添加了DNS记录"
echo "  2. 等待DNS传播（10分钟到24小时）"
echo "  3. 清除本地DNS缓存: sudo dscacheutil -flushcache"
echo ""
echo "如果记录已生效但阿里云显示未验证："
echo "  1. 在阿里云控制台点击'验证'按钮"
echo "  2. 等待几分钟后重试"
echo "  3. 联系阿里云技术支持"
echo ""
