#!/bin/bash
# 一键打包Mac应用 - 简化版

echo "🚀 AI助理 - Mac应用一键打包工具"
echo "=================================="
echo ""

# 检查依赖
echo "📋 检查依赖..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要Python 3。请安装: brew install python3"
    exit 1
fi

if ! pip3 show pyinstaller &> /dev/null; then
    echo "📦 安装PyInstaller..."
    pip3 install pyinstaller
fi

echo "✅ 依赖检查完成"
echo ""

# 清理
echo "🧹 清理旧文件..."
rm -rf dist build *.spec mac_app_dist
echo ""

# 打包
echo "📦 开始打包Python应用..."
echo "   这可能需要几分钟，请耐心等待..."
echo ""

python3 -m PyInstaller \
    --name="AI个人助理" \
    --windowed \
    --onefile \
    --hidden-import=pymysql \
    --hidden-import=pymysql.cursors \
    --clean \
    --noconfirm \
    app_launcher.py

if [ $? -ne 0 ]; then
    echo "❌ 打包失败"
    exit 1
fi

echo ""
echo "✅ 打包完成！"
echo ""

# 创建发布目录
echo "📁 创建发布目录..."
mkdir -p mac_app_dist
cp -r "dist/AI个人助理.app" mac_app_dist/

# 创建使用说明
cat > mac_app_dist/README.txt << 'EOF'
AI个人助理 - 使用说明
================================

安装步骤：
1. 将 "AI个人助理.app" 拖到"应用程序"文件夹
2. 右键点击应用 -> 选择"打开"（首次需要）

首次配置：
应用首次启动会自动创建配置文件在：
~/Library/Application Support/AIAssistant/

需要配置两个文件：

1️⃣ mysql_config.json - 云数据库配置
{
  "host": "你的云服务器IP",
  "port": 3306,
  "user": "ai_assistant",
  "password": "数据库密码",
  "database": "ai_assistant",
  "charset": "utf8mb4"
}

2️⃣ ai_config.json - AI配置（可选）
{
  "api_key": "你的通义千问API_KEY",
  ...
}

使用方法：
1. 双击打开"AI个人助理"
2. 浏览器自动打开 http://localhost:8000
3. 注册/登录使用

数据同步：
✅ 所有数据存储在云端MySQL
✅ 换设备后登录即可访问
✅ 支持多设备同时使用

常见问题：
Q: 无法打开？
A: 右键 -> 打开 -> 确认打开

Q: 如何停止？
A: 关闭浏览器，活动监视器中结束进程

Q: 如何卸载？
A: 删除应用 + 删除配置目录
   ~/Library/Application Support/AIAssistant/
EOF

echo "✅ 发布目录创建完成"
echo ""

echo "=================================="
echo "🎉 打包成功！"
echo "=================================="
echo ""
echo "输出位置: mac_app_dist/"
echo ""
echo "文件列表:"
ls -lh mac_app_dist/
echo ""
echo "下一步:"
echo "1. 测试: open 'mac_app_dist/AI个人助理.app'"
echo "2. 分发: 将 mac_app_dist 文件夹压缩后分享"
echo ""
echo "💡 提示: 用户收到后只需解压，双击.app即可使用"
echo ""
