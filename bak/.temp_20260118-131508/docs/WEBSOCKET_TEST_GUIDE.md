# WebSocket 推送功能测试指南

## 当前状态

✅ **WebSocket 测试服务器已启动**
- 地址: `ws://localhost:8001` (本地测试)
- 地址: `ws://47.109.148.176:8001` (云服务器，需要先部署)
- 进程ID: 36521
- 状态: 运行中

## 测试步骤

### 1. 准备移动端应用

确保移动端代码中的 WebSocket 地址指向本地测试服务器：

在 `lib/services/websocket_service.dart` 中临时修改：
```dart
// 测试时使用本地地址
static const String wsUrl = 'ws://localhost:8001';

// 或者如果在真机上测试，使用电脑的局域网IP
// static const String wsUrl = 'ws://192.168.x.x:8001';
```

### 2. 运行移动应用

```bash
cd ai-assistant-mobile
flutter run -d ios
```

### 3. 登录应用

1. 打开应用
2. 使用任意账号登录
3. 观察控制台输出，应该看到：
   - `✅ WebSocket 连接已建立`
   - `✅ 通知服务初始化完成`

### 4. 观察服务器日志

在另一个终端窗口查看服务器日志：

```bash
tail -f /var/folders/qm/cmdpr7815z3cgx10jvk4k9vm0000gn/T/claude/-Users-gj----ai--new/tasks/b6f8646.output
```

应该看到：
- `📱 新客户端连接`
- `✅ 用户 X 认证成功`
- `📊 当前在线用户数: 1`

### 5. 等待测试提醒

服务器会每 30 秒自动发送一次测试提醒。你应该会：
1. 在移动端收到本地通知
2. 看到通知内容："测试提醒 - HH:MM:SS"

### 6. 验证心跳机制

每 30 秒，移动端会发送心跳包，服务器日志会显示：
- `💓 收到用户 X 的心跳`

## 故障排查

### 问题1: 移动端连接失败

**症状**: 应用日志显示 `❌ WebSocket 连接失败`

**解决方案**:
1. 检查 WebSocket 服务器是否运行：`lsof -i :8001`
2. 检查防火墙是否阻止连接
3. 如果在真机测试，确保手机和电脑在同一局域网

### 问题2: 收不到通知

**症状**: WebSocket 连接成功，但收不到通知

**解决方案**:
1. 检查应用是否授予了通知权限
2. 查看移动端日志是否有错误
3. 确认通知服务是否初始化成功

### 问题3: 连接频繁断开

**症状**: 日志显示反复连接和断开

**解决方案**:
1. 检查网络稳定性
2. 查看是否有异常错误日志
3. 确认心跳机制是否正常工作

## 停止测试服务器

```bash
# 查找进程ID
ps aux | grep test_websocket_simple

# 停止服务器
kill 36521

# 或者使用 pkill
pkill -f test_websocket_simple
```

## 下一步

测试成功后，需要：

1. **部署到云服务器**:
   ```bash
   # 在服务器上
   cd /var/www/ai-assistant
   pip3 install websockets
   # 修改 assistant_web.py 启动 WebSocket 服务器
   sudo supervisorctl restart ai-assistant
   ```

2. **修改移动端配置**:
   ```dart
   // 改回云服务器地址
   static const String wsUrl = 'ws://47.109.148.176:8001';
   ```

3. **配置防火墙**:
   ```bash
   sudo ufw allow 8001/tcp
   sudo ufw reload
   ```

## 测试检查清单

- [ ] WebSocket 服务器启动成功
- [ ] 移动端成功连接到 WebSocket
- [ ] 收到测试提醒通知
- [ ] 心跳机制正常工作
- [ ] 断开重连机制正常
- [ ] 登出时正确断开连接

## 预期结果

如果一切正常，你应该看到：

1. **服务器端**:
   ```
   📱 新客户端连接: ('127.0.0.1', 54321)
   ✅ 用户 1 认证成功
   📊 当前在线用户数: 1
   💓 收到用户 1 的心跳
   📢 发送测试提醒到 1 个用户...
   ✅ 已发送测试提醒到用户 1
   ```

2. **移动端**:
   - 收到系统通知
   - 通知标题: "📢 任务提醒"
   - 通知内容: "测试提醒 - HH:MM:SS"

3. **应用日志**:
   ```
   ✅ 通知服务初始化完成
   🔌 正在连接 WebSocket: ws://localhost:8001
   ✅ WebSocket 已连接
   ✅ WebSocket 认证成功
   📨 收到 WebSocket 消息: reminder
   ✅ 已显示通知: 📢 任务提醒
   ```
