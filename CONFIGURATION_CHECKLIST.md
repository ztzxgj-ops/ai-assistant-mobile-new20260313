# FCM推送通知配置检查清单

## ✅ 已完成的配置

### 服务器端
- [x] fcm_push_service.py 已创建
- [x] DeviceTokenManager 已添加到 mysql_manager.py
- [x] reminder_scheduler.py 已集成FCM推送
- [x] assistant_web.py 已添加API端点
- [x] database_device_tokens.sql 已创建
- [x] firebase-admin Python包已安装
- [x] 所有Python代码语法验证通过

### 移动端
- [x] firebase_core 依赖已添加 (v3.15.2)
- [x] firebase_messaging 依赖已添加 (v15.2.10)
- [x] FirebaseMessagingService 已创建
- [x] Flutter依赖已安装

### 文档和脚本
- [x] FIREBASE_PUSH_SETUP_GUIDE.md 配置指南
- [x] FCM_PUSH_TEST_GUIDE.md 测试指南
- [x] deploy_fcm_push.sh 部署脚本
- [x] firebase_config.json.example 配置示例

---

## ⚠️ 需要手动完成的配置

### 1. Firebase Console配置

#### 1.1 创建/配置Firebase项目
- [ ] 访问 https://console.firebase.google.com/
- [ ] 创建或选择项目

#### 1.2 添加iOS应用
- [ ] 项目设置 → 添加应用 → iOS
- [ ] Bundle ID: `com.gaojun.wangleme`
- [ ] 下载 `GoogleService-Info.plist`
- [ ] 放置到: `ai-assistant-mobile/ios/Runner/GoogleService-Info.plist`

#### 1.3 添加Android应用
- [ ] 项目设置 → 添加应用 → Android
- [ ] Package name: `com.example.ai_personal_assistant`
- [ ] 下载 `google-services.json`
- [ ] 放置到: `ai-assistant-mobile/android/app/google-services.json`

#### 1.4 下载服务器配置
- [ ] 项目设置 → 服务账号
- [ ] 生成新的私钥
- [ ] 下载JSON文件
- [ ] 重命名为 `firebase_config.json`
- [ ] 放置到项目根目录

#### 1.5 配置APNs (iOS推送)
- [ ] 访问 https://developer.apple.com/account/resources/authkeys/list
- [ ] 创建APNs密钥 (.p8文件)
- [ ] 记录 Key ID 和 Team ID
- [ ] 在Firebase控制台上传APNs密钥
  - 项目设置 → Cloud Messaging → Apple应用配置

---

### 2. iOS项目配置

#### 2.1 在Xcode中添加配置文件
```bash
cd ai-assistant-mobile/ios
open Runner.xcworkspace
```

在Xcode中：
- [ ] 右键点击Runner → Add Files to Runner
- [ ] 选择 `GoogleService-Info.plist`
- [ ] 勾选 "Copy items if needed"
- [ ] 勾选 "Add to targets: Runner"

#### 2.2 修改Podfile
在 `ai-assistant-mobile/ios/Podfile` 中添加：
```ruby
target 'Runner' do
  use_frameworks!
  flutter_install_all_ios_pods File.dirname(File.realpath(__FILE__))

  # 添加Firebase pods
  pod 'Firebase/Messaging'
end
```

#### 2.3 安装Pods
```bash
cd ai-assistant-mobile/ios
pod install
```

#### 2.4 修改AppDelegate.swift
在 `ai-assistant-mobile/ios/Runner/AppDelegate.swift` 中：
- [ ] 添加 `import Firebase`
- [ ] 在 `didFinishLaunchingWithOptions` 中添加 `FirebaseApp.configure()`
- [ ] 添加 `didRegisterForRemoteNotificationsWithDeviceToken` 方法

#### 2.5 添加Capabilities
在Xcode中：
- [ ] 选择Runner target → Signing & Capabilities
- [ ] 添加 "Push Notifications"
- [ ] 添加 "Background Modes" → 勾选 "Remote notifications"

---

### 3. Android项目配置

#### 3.1 修改项目级build.gradle
在 `ai-assistant-mobile/android/build.gradle` 中添加：
```gradle
dependencies {
    classpath 'com.google.gms:google-services:4.4.0'
}
```

#### 3.2 修改应用级build.gradle.kts
在 `ai-assistant-mobile/android/app/build.gradle.kts` 末尾添加：
```kotlin
plugins {
    id("com.google.gms.google-services")
}
```

#### 3.3 确认google-services.json位置
- [ ] 文件位于: `ai-assistant-mobile/android/app/google-services.json`

---

### 4. Flutter应用代码集成

#### 4.1 修改main.dart
在 `lib/main.dart` 中添加：

```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'services/firebase_messaging_service.dart';

// 后台消息处理器
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  print('📨 收到后台消息: ${message.notification?.title}');
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 初始化Firebase
  await Firebase.initializeApp();

  // 设置后台消息处理器
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  // 初始化Firebase Messaging服务
  final firebaseMessaging = FirebaseMessagingService();
  await firebaseMessaging.initialize();

  runApp(MyApp());
}
```

#### 4.2 在登录后注册Token
在用户登录成功后：
```dart
final firebaseMessaging = FirebaseMessagingService();
await firebaseMessaging.registerToken(userToken);
```

#### 4.3 在登出时取消注册
在用户登出时：
```dart
final firebaseMessaging = FirebaseMessagingService();
await firebaseMessaging.unregisterToken(userToken);
```

---

### 5. 服务器部署

#### 5.1 上传firebase_config.json
- [ ] 将 `firebase_config.json` 上传到服务器
- [ ] 位置: `/var/www/ai-assistant/firebase_config.json`
- [ ] 权限: `chmod 600 firebase_config.json`

#### 5.2 创建数据库表
```bash
ssh root@47.109.148.176
cd /var/www/ai-assistant
mysql -u ai_assistant -p ai_assistant < database_device_tokens.sql
```

#### 5.3 运行部署脚本
```bash
cd /Users/gj/编程/ai助理new
./deploy_fcm_push.sh
```

或手动部署：
```bash
# 上传文件
scp fcm_push_service.py root@47.109.148.176:/var/www/ai-assistant/
scp mysql_manager.py root@47.109.148.176:/var/www/ai-assistant/
scp reminder_scheduler.py root@47.109.148.176:/var/www/ai-assistant/
scp assistant_web.py root@47.109.148.176:/var/www/ai-assistant/
scp firebase_config.json root@47.109.148.176:/var/www/ai-assistant/

# 重启服务
ssh root@47.109.148.176 "sudo supervisorctl restart ai-assistant"
```

---

## 🧪 测试步骤

### 测试1：验证服务器配置
```bash
ssh root@47.109.148.176
cd /var/www/ai-assistant
ls -la firebase_config.json
python3 -c "from fcm_push_service import get_fcm_service; print(get_fcm_service().initialized)"
```

### 测试2：测试设备Token注册
1. 在真机上运行应用
2. 登录
3. 查看控制台输出FCM Token
4. 检查数据库：
```sql
SELECT * FROM device_tokens WHERE user_id = YOUR_USER_ID;
```

### 测试3：测试推送API
```bash
curl -X POST http://47.109.148.176/ai/api/device/test-push \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

### 测试4：端到端提醒测试
1. 创建1分钟后的提醒
2. 关闭应用
3. 等待推送通知

---

## 📝 配置完成后的验证

- [ ] 服务器日志显示 "FCM推送服务已初始化"
- [ ] 移动应用显示 "Firebase Messaging已初始化"
- [ ] 设备Token已保存到数据库
- [ ] 测试推送API返回成功
- [ ] 关闭应用后能收到推送通知
- [ ] iOS和Android都能正常接收推送

---

## 🔗 相关文档

- **详细配置**: FIREBASE_PUSH_SETUP_GUIDE.md
- **测试指南**: FCM_PUSH_TEST_GUIDE.md
- **部署脚本**: deploy_fcm_push.sh

---

## ⚠️ 注意事项

1. **安全性**：
   - 不要将firebase_config.json提交到git
   - 添加到.gitignore：
     ```
     firebase_config.json
     ios/Runner/GoogleService-Info.plist
     android/app/google-services.json
     ```

2. **测试环境**：
   - iOS推送必须在真机上测试
   - 模拟器不支持推送通知

3. **网络要求**：
   - Android需要访问Google服务
   - 确保网络可以连接Firebase

---

## 📞 需要帮助？

如果遇到问题：
1. 查看 FCM_PUSH_TEST_GUIDE.md 的故障排查部分
2. 检查服务器日志: `tail -f /var/log/ai-assistant.log`
3. 检查Firebase控制台的Cloud Messaging日志

---

**当前状态**: 代码开发和本地配置已完成，等待Firebase配置文件和服务器部署。
