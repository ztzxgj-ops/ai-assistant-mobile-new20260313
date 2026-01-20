#!/bin/bash
# MySQL远程连接诊断脚本
# 在云服务器上运行此脚本以检查MySQL配置

echo "================================"
echo "MySQL 远程连接诊断工具"
echo "================================"
echo ""

# 检查MySQL服务状态
echo "1️⃣  检查MySQL服务状态..."
if systemctl is-active --quiet mysql; then
    echo "✅ MySQL服务运行中"
else
    echo "❌ MySQL服务未运行"
    echo "   尝试启动: sudo systemctl start mysql"
    exit 1
fi
echo ""

# 检查MySQL监听端口
echo "2️⃣  检查MySQL监听端口..."
MYSQL_LISTEN=$(sudo netstat -tlnp | grep 3306)
if [ -z "$MYSQL_LISTEN" ]; then
    echo "❌ MySQL未监听3306端口"
    exit 1
fi

echo "$MYSQL_LISTEN"
if echo "$MYSQL_LISTEN" | grep -q "0.0.0.0:3306"; then
    echo "✅ MySQL监听所有IP (0.0.0.0:3306)"
elif echo "$MYSQL_LISTEN" | grep -q "127.0.0.1:3306"; then
    echo "⚠️  MySQL只监听本地 (127.0.0.1:3306)"
    echo ""
    echo "需要修改配置文件:"
    echo "1. 编辑: sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf"
    echo "2. 找到: bind-address = 127.0.0.1"
    echo "3. 改为: bind-address = 0.0.0.0"
    echo "4. 重启: sudo systemctl restart mysql"
    echo ""
fi
echo ""

# 检查防火墙状态
echo "3️⃣  检查防火墙状态..."
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status | grep "3306")
    if [ -z "$UFW_STATUS" ]; then
        echo "⚠️  UFW未配置3306端口规则"
        echo "   添加规则: sudo ufw allow 3306/tcp"
    else
        echo "✅ UFW已配置3306规则:"
        echo "$UFW_STATUS"
    fi
else
    echo "ℹ️  UFW未安装（可能使用其他防火墙）"
fi
echo ""

# 检查iptables
echo "4️⃣  检查iptables规则..."
IPTABLES_3306=$(sudo iptables -L -n | grep 3306)
if [ -z "$IPTABLES_3306" ]; then
    echo "ℹ️  iptables无3306相关规则（可能在其他链中）"
else
    echo "$IPTABLES_3306"
fi
echo ""

# 检查MySQL用户权限
echo "5️⃣  检查MySQL用户权限..."
echo "请输入MySQL root密码:"
mysql -u root -p -e "SELECT user, host FROM mysql.user WHERE user='ai_assistant';" 2>/dev/null

if [ $? -eq 0 ]; then
    echo ""
    echo "说明："
    echo "  - host='%' : 允许所有IP连接 ✅"
    echo "  - host='localhost' : 只允许本地连接 ❌"
    echo ""
    echo "如果host为localhost，执行以下SQL修复："
    echo "  DROP USER 'ai_assistant'@'localhost';"
    echo "  CREATE USER 'ai_assistant'@'%' IDENTIFIED BY 'ai_assistant_2024';"
    echo "  GRANT ALL PRIVILEGES ON ai_assistant.* TO 'ai_assistant'@'%';"
    echo "  FLUSH PRIVILEGES;"
else
    echo "⚠️  无法连接MySQL或权限不足"
fi
echo ""

# 总结
echo "================================"
echo "诊断完成！"
echo "================================"
echo ""
echo "下一步："
echo "1. 如果MySQL绑定127.0.0.1 → 修改配置文件改为0.0.0.0"
echo "2. 如果用户host为localhost → 修改为'%'"
echo "3. 检查阿里云安全组是否开放3306端口（最重要！）"
echo ""
echo "安全组配置："
echo "  - 登录: https://ecs.console.aliyun.com"
echo "  - 找到实例 → 安全组 → 配置规则 → 入方向"
echo "  - 添加规则: TCP 3306/3306 授权对象 0.0.0.0/0"
echo ""
