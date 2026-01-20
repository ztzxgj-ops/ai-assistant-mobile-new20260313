# WebSocket 推送通知部署指南

## 服务器端配置

### 1. 安装 Python websockets 库

```bash
# 在服务器上执行
pip3 install websockets
```

### 2. 修改 assistant_web.py 启动 WebSocket 服务器

在 `assistant_web.py` 的主函数中添加：

```python
from reminder_scheduler import get_global_scheduler
from mysql_manager import MySQLManager

# 在 main 函数中
if __name__ == '__main__':
    # 初始化数据库
    db = MySQLManager()

    # 启动提醒调度器（会自动启动 WebSocket 服务器）
    scheduler = get_global_scheduler(db_manager=db)
    scheduler.start()

    # 启动 HTTP 服务器
    # ... 现有代码
```

### 3. 配置防火墙开放端口 8001

```bash
# 开放 WebSocket 端口
sudo ufw allow 8001/tcp
sudo ufw reload
```

### 4. 配置 Nginx 反向代理（可选）

如果需要通过 Nginx 代理 WebSocket：

```nginx
# 在 /etc/nginx/sites-available/default 中添加
location /ws/ {
    proxy_pass http://127.0.0.1:8001/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 86400;
}
```

然后重启 Nginx：
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 移动端配置

### iOS 通知权限配置

在 `ios/Runner/Info.plist` 中添加：

```xml
<key>UIBackgroundModes</key>
<array>
    <string>remote-notification</string>
    <string>fetch</string>
</array>
```

### Android 通知权限配置

在 `android/app/src/main/AndroidManifest.xml` 中添加：

```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
<uses-permission android:name="android.permission.VIBRATE"/>
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
```

## 测试

### 1. 测试 WebSocket 连接

```bash
# 在服务器上检查 WebSocket 端口是否监听
netstat -tlnp | grep 8001
```

### 2. 测试提醒推送

1. 登录移动应用
2. 通过 AI 对话创建一个提醒："提醒我 1 分钟后测试通知"
3. 等待 1 分钟，应该会收到推送通知

### 3. 查看日志

```bash
# 服务器端日志
tail -f /var/log/ai-assistant.log

# 移动端日志
# 在 Xcode 或 Android Studio 中查看控制台输出
```

## 故障排查

### WebSocket 连接失败

1. 检查服务器防火墙是否开放 8001 端口
2. 检查 websockets 库是否安装：`pip3 list | grep websockets`
3. 检查服务器日志是否有错误信息

### 收不到通知

1. 检查移动端是否授予了通知权限
2. 检查 WebSocket 是否连接成功（查看应用日志）
3. 检查服务器端提醒调度器是否正常运行
4. 确认提醒时间是否已到

### 应用在后台时收不到通知

- iOS: 需要配置后台模式和推送证书
- Android: 需要处理电池优化设置

## 注意事项

1. WebSocket 连接在应用进入后台时可能会断开，需要在应用回到前台时重新连接
2. 建议实现心跳机制保持连接活跃（已实现，30秒一次）
3. 生产环境建议使用 WSS（WebSocket over TLS）加密连接
4. 考虑实现离线消息队列，确保用户不在线时的提醒不会丢失
