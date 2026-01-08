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
