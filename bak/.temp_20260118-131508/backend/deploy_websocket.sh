#!/bin/bash
# WebSocket 推送功能云服务器部署脚本

SERVER_IP="47.109.148.176"
SERVER_USER="root"
PROJECT_DIR="/var/www/ai-assistant"

echo "=========================================="
echo "WebSocket 推送功能部署到云服务器"
echo "=========================================="
echo ""

# 1. 上传文件到服务器
echo "1️⃣ 上传文件到服务器..."
scp websocket_server.py ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/
scp test_websocket_simple.py ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/

if [ $? -eq 0 ]; then
    echo "✅ 文件上传成功"
else
    echo "❌ 文件上传失败"
    exit 1
fi

echo ""
echo "2️⃣ 在服务器上安装依赖..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
cd /var/www/ai-assistant

# 安装 websockets 库
pip3 install websockets

if [ $? -eq 0 ]; then
    echo "✅ websockets 库安装成功"
else
    echo "❌ websockets 库安装失败"
    exit 1
fi
EOF

echo ""
echo "3️⃣ 配置防火墙..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
# 开放 WebSocket 端口
sudo ufw allow 8001/tcp
sudo ufw reload

echo "✅ 防火墙配置完成"
EOF

echo ""
echo "4️⃣ 启动测试服务器..."
echo "请选择启动方式："
echo "  a) 启动测试服务器（临时测试，30秒发送一次提醒）"
echo "  b) 集成到 assistant_web.py（生产环境）"
echo ""
read -p "请选择 (a/b): " choice

if [ "$choice" = "a" ]; then
    echo ""
    echo "启动测试服务器..."
    ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
cd /var/www/ai-assistant

# 停止可能存在的旧进程
pkill -f test_websocket_simple.py

# 启动测试服务器（后台运行）
nohup python3 test_websocket_simple.py > /tmp/websocket_test.log 2>&1 &

sleep 2

# 检查是否启动成功
if lsof -i :8001 > /dev/null 2>&1; then
    echo "✅ WebSocket 测试服务器已启动"
    echo "📊 查看日志: tail -f /tmp/websocket_test.log"
else
    echo "❌ WebSocket 服务器启动失败"
    exit 1
fi
EOF

elif [ "$choice" = "b" ]; then
    echo ""
    echo "⚠️ 需要手动修改 assistant_web.py"
    echo ""
    echo "请在 assistant_web.py 的主函数中添加："
    echo ""
    cat << 'PYTHON'
from reminder_scheduler import get_global_scheduler
from mysql_manager import MySQLManager

# 在 if __name__ == '__main__': 中添加
db = MySQLManager()
scheduler = get_global_scheduler(db_manager=db)
scheduler.start()
PYTHON
    echo ""
    echo "然后重启服务："
    echo "  sudo supervisorctl restart ai-assistant"
else
    echo "❌ 无效的选择"
    exit 1
fi

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "📱 现在可以在移动端测试了"
echo ""
echo "测试步骤："
echo "1. 打开移动应用并登录"
echo "2. 应用会自动连接到 ws://47.109.148.176:8001"
echo "3. 等待接收测试提醒（每30秒一次）"
echo ""
echo "查看服务器日志："
echo "  ssh ${SERVER_USER}@${SERVER_IP} 'tail -f /tmp/websocket_test.log'"
echo ""
echo "停止测试服务器："
echo "  ssh ${SERVER_USER}@${SERVER_IP} 'pkill -f test_websocket_simple.py'"
echo ""
