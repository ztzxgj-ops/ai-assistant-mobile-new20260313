# FCM推送通知测试指南

## 测试环境准备

### 1. 服务器端准备

确保以下文件已部署到服务器：
- ✅ fcm_push_service.py
- ✅ mysql_manager.py (包含DeviceTokenManager)
- ✅ reminder_scheduler.py (已集成FCM)
- ✅ assistant_web.py (包含API端点)
- ✅ firebase_config.json (Firebase Admin SDK配置)
- ✅ database_device_tokens表已创建

### 2. 移动端准备

确保Flutter应用已完成以下配置：
- ✅ firebase_core和firebase_messaging依赖已添加
- ✅ GoogleService-Info.plist (iOS)
- ✅ google-services.json (Android)
- ✅ Firebase初始化代码已添加到main.dart
- ✅ FirebaseMessagingService已集成

---

## 测试步骤

### 测试1：验证服务器端配置

#### 1.1 检查Firebase配置

```bash
# SSH到服务器
ssh root@47.109.148.176

# 检查firebase_config.json是否存在
cd /var/www/ai-assistant
ls -la firebase_config.json

# 检查文件内容（确保有project_id和private_key）
cat firebase_config.json | grep "project_id"
```

#### 1.2 检查数据库表

```bash
# 连接数据库
mysql -u ai_assistant -p ai_assistant

# 检查device_tokens表
SHOW TABLES LIKE 'device_tokens';
DESC device_tokens;

# 退出
exit
```

#### 1.3 检查服务状态

```bash
# 检查服务是否运行
sudo supervisorctl status ai-assistant

# 查看日志
tail -f /var/log/ai-assistant.log
```

**预期结果：**
- ✅ firebase_config.json存在且格式正确
- ✅ device_tokens表已创建
- ✅ 服务正常运行
- ✅ 日志中显示"FCM推送服务已初始化"

---

### 测试2：移动端设备Token注册

#### 2.1 启动移动应用

```bash
# iOS
cd ai-assistant-mobile
flutter run -d ios

# Android
flutter run -d android
```

#### 2.2 登录应用

1. 打开应用
2. 输入用户名和密码登录
3. 观察控制台输出

**预期输出：**
```
✅ 用户已授权推送通知
📱 FCM Token: xxxxxxxxxxxxxx
✅ Firebase Messaging已初始化
✅ 设备Token已注册到服务器
```

#### 2.3 验证Token已保存

在服务器上查询数据库：

```bash
mysql -u ai_assistant -p ai_assistant

SELECT * FROM device_tokens WHERE user_id = YOUR_USER_ID;
```

**预期结果：**
- ✅ 数据库中有一条记录
- ✅ device_token字段不为空
- ✅ device_type为'ios'或'android'
- ✅ is_active为1

---

### 测试3：测试推送API

#### 3.1 获取用户Token

```bash
# 登录获取token
curl -X POST http://47.109.148.176/ai/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_USERNAME","password":"YOUR_PASSWORD"}'

# 保存返回的token
export USER_TOKEN="返回的token"
```

#### 3.2 测试推送通知

```bash
curl -X POST http://47.109.148.176/ai/api/device/test-push \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json"
```

**预期响应：**
```json
{
  "status": "success",
  "message": "推送通知已发送",
  "result": {
    "success": true,
    "message": "消息已发送: projects/xxx/messages/xxx"
  }
}
```

**预期效果：**
- ✅ 手机收到推送通知
- ✅ 通知标题："📢 任务提醒"
- ✅ 通知内容："这是一条测试推送通知"
- ✅ 即使app在后台或关闭也能收到

---

### 测试4：提醒功能端到端测试

#### 4.1 创建提醒

在移动应用或Web界面中创建一个提醒：
- 内容："测试提醒"
- 时间：1分钟后

#### 4.2 关闭应用

- iOS：双击Home键，向上滑动关闭应用
- Android：从最近任务中移除应用

#### 4.3 等待提醒时间

等待1分钟后，观察是否收到推送通知。

**预期效果：**
- ✅ 即使app完全关闭，仍然收到推送通知
- ✅ 通知内容为"测试提醒"
- ✅ 点击通知可以打开应用

#### 4.4 查看服务器日志

```bash
# 查看提醒发送日志
tail -f /var/log/ai-assistant.log | grep "FCM"
```

**预期日志：**
```
📱 准备发送FCM推送到 1 个设备
✅ FCM推送成功: {'success': True, 'message': '...'}
```

---

### 测试5：多设备推送测试

#### 5.1 在多个设备上登录

1. 在iPhone上登录
2. 在Android手机上登录
3. 或在同一设备上卸载重装后再次登录

#### 5.2 查看设备列表

```bash
curl -X GET http://47.109.148.176/ai/api/device/list \
  -H "Authorization: Bearer $USER_TOKEN"
```

**预期响应：**
```json
{
  "status": "success",
  "devices": [
    {
      "id": 1,
      "device_token": "xxx",
      "device_type": "ios",
      "device_name": "iPhone",
      "is_active": 1,
      ...
    },
    {
      "id": 2,
      "device_token": "yyy",
      "device_type": "android",
      "device_name": "Android",
      "is_active": 1,
      ...
    }
  ]
}
```

#### 5.3 测试多设备推送

创建一个提醒，所有登录的设备都应该收到通知。

**预期效果：**
- ✅ 所有设备都收到推送
- ✅ 通知内容一致
- ✅ 时间准确

---

### 测试6：iOS特定测试

#### 6.1 前台通知

1. 打开应用
2. 创建一个立即触发的提醒
3. 保持应用在前台

**预期效果：**
- ✅ 收到通知横幅
- ✅ 有声音提示
- ✅ 角标数字增加

#### 6.2 后台通知

1. 创建提醒
2. 按Home键将应用切到后台
3. 等待提醒触发

**预期效果：**
- ✅ 锁屏上显示通知
- ✅ 通知中心有记录
- ✅ 角标数字更新

#### 6.3 锁屏通知

1. 创建提醒
2. 锁定设备
3. 等待提醒触发

**预期效果：**
- ✅ 锁屏界面显示通知
- ✅ 有声音和振动
- ✅ 可以从锁屏直接打开应用

---

### 测试7：Android特定测试

#### 7.1 通知渠道

检查通知设置：
1. 长按通知
2. 点击"设置"
3. 查看通知渠道配置

**预期效果：**
- ✅ 有"FCM推送通知"渠道
- ✅ 重要性设置为"高"
- ✅ 允许声音和振动

#### 7.2 后台限制

测试不同的后台限制：
1. 设置 → 应用 → 忘了么 → 电池
2. 尝试不同的电池优化设置

**预期效果：**
- ✅ 即使有电池优化，仍能收到推送
- ✅ FCM推送不受Doze模式影响

---

## 故障排查

### 问题1：收不到推送通知

**检查清单：**
1. ✅ Firebase配置文件是否正确
2. ✅ APNs密钥是否已上传（iOS）
3. ✅ google-services.json是否正确（Android）
4. ✅ 设备token是否已注册到数据库
5. ✅ 服务器日志是否有错误
6. ✅ 网络连接是否正常

**调试命令：**
```bash
# 查看服务器日志
tail -f /var/log/ai-assistant.log | grep -E "FCM|推送|token"

# 查看数据库中的token
mysql -u ai_assistant -p ai_assistant -e "SELECT * FROM device_tokens WHERE is_active=1;"

# 测试Firebase连接
python3 -c "from fcm_push_service import get_fcm_service; s=get_fcm_service(); print('FCM初始化:', s.initialized)"
```

### 问题2：iOS推送不工作

**可能原因：**
1. APNs密钥未上传或配置错误
2. Bundle ID不匹配
3. 推送证书过期
4. 在模拟器上测试（模拟器不支持推送）

**解决方案：**
1. 检查Firebase控制台的APNs配置
2. 确认Bundle ID为：com.gaojun.wangleme
3. 必须在真机上测试
4. 检查Xcode中的Capabilities配置

### 问题3：Android推送不工作

**可能原因：**
1. google-services.json配置错误
2. Package name不匹配
3. Google Play Services未安装
4. 网络问题（需要访问Google服务）

**解决方案：**
1. 确认Package name为：com.example.ai_personal_assistant
2. 检查google-services.json中的package_name
3. 确保设备已安装Google Play Services
4. 检查网络连接

### 问题4：Token注册失败

**检查：**
```bash
# 查看API日志
tail -f /var/log/ai-assistant.log | grep "register-token"

# 测试API端点
curl -X POST http://47.109.148.176/ai/api/device/register-token \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_token": "test_token",
    "device_type": "ios",
    "device_name": "Test Device"
  }'
```

---

## 性能测试

### 测试推送延迟

创建多个提醒，记录从触发时间到收到通知的延迟：

```bash
# 创建测试脚本
for i in {1..10}; do
  echo "创建提醒 $i"
  # 调用API创建提醒
  sleep 1
done

# 观察推送延迟
```

**预期延迟：**
- 服务器检查间隔：30秒
- FCM推送延迟：1-3秒
- 总延迟：< 35秒

### 测试并发推送

模拟多个用户同时收到提醒：

```bash
# 在数据库中创建多个即将触发的提醒
# 观察服务器负载和推送成功率
```

---

## 测试完成清单

- [ ] 服务器端配置验证
- [ ] 设备Token注册成功
- [ ] 测试推送API工作正常
- [ ] 提醒端到端测试通过
- [ ] 多设备推送测试通过
- [ ] iOS前台/后台/锁屏通知都正常
- [ ] Android通知正常显示
- [ ] 推送延迟在可接受范围内
- [ ] 无明显错误日志

---

## 测试报告模板

```
测试日期：____年__月__日
测试人员：________
测试环境：
  - 服务器：47.109.148.176
  - iOS设备：_______ (iOS版本：___)
  - Android设备：_______ (Android版本：___)

测试结果：
  ✅/❌ 服务器端配置
  ✅/❌ Token注册
  ✅/❌ 测试推送API
  ✅/❌ 提醒端到端
  ✅/❌ 多设备推送
  ✅/❌ iOS通知
  ✅/❌ Android通知

问题记录：
  1. _______________
  2. _______________

备注：
  _______________
```

---

## 下一步

测试通过后：
1. 在生产环境中监控推送成功率
2. 收集用户反馈
3. 优化推送内容和时机
4. 考虑添加推送统计功能

测试失败时：
1. 查看故障排查部分
2. 检查日志文件
3. 联系技术支持
