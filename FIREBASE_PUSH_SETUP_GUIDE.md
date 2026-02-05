# Firebase推送通知配置指南

## 概述

本指南将帮助您完成iOS和Android的Firebase Cloud Messaging (FCM)推送通知配置。

## 前置要求

1. Firebase项目（已创建）
2. iOS: Apple Developer账号
3. Android: 无特殊要求

---

## 第一步：获取Firebase配置文件

### 1.1 访问Firebase控制台

访问 https://console.firebase.google.com/

### 1.2 下载iOS配置文件

1. 进入项目设置
2. 选择iOS应用（如果没有，点击"添加应用" → iOS）
3. Bundle ID输入：`com.gaojun.wangleme`
4. 下载 `GoogleService-Info.plist`
5. 将文件放到：`ai-assistant-mobile/ios/Runner/GoogleService-Info.plist`

### 1.3 下载Android配置文件

1. 进入项目设置
2. 选择Android应用（如果没有，点击"添加应用" → Android）
3. Package name输入：`com.example.ai_personal_assistant`
4. 下载 `google-services.json`
5. 将文件放到：`ai-assistant-mobile/android/app/google-services.json`

### 1.4 下载服务器端配置文件

1. 进入项目设置 → 服务账号
2. 点击"生成新的私钥"
3. 下载JSON文件
4. 重命名为 `firebase_config.json`
5. 将文件放到服务器项目根目录：`/Users/gj/编程/ai助理new/firebase_config.json`

---

## 第二步：iOS配置

### 2.1 配置APNs认证密钥

1. 访问 [Apple Developer](https://developer.apple.com/account/resources/authkeys/list)
2. 创建新的密钥（Keys）
3. 勾选"Apple Push Notifications service (APNs)"
4. 下载密钥文件（.p8文件）
5. 记录Key ID和Team ID

### 2.2 上传APNs密钥到Firebase

1. 在Firebase控制台，进入项目设置 → Cloud Messaging
2. 在"Apple应用配置"部分，点击"上传"
3. 上传.p8文件
4. 输入Key ID和Team ID

### 2.3 修改iOS项目配置

#### 2.3.1 在Xcode中添加GoogleService-Info.plist

```bash
cd ai-assistant-mobile/ios
open Runner.xcworkspace
```

在Xcode中：
1. 右键点击Runner文件夹
2. 选择"Add Files to Runner"
3. 选择`GoogleService-Info.plist`
4. 确保"Copy items if needed"被勾选
5. 确保"Add to targets"中Runner被勾选

#### 2.3.2 修改Podfile

在`ai-assistant-mobile/ios/Podfile`的`target 'Runner' do`部分添加：

```ruby
target 'Runner' do
  use_frameworks!

  flutter_install_all_ios_pods File.dirname(File.realpath(__FILE__))

  # 添加Firebase pods
  pod 'Firebase/Messaging'

  target 'RunnerTests' do
    inherit! :search_paths
  end
end
```

#### 2.3.3 安装pods

```bash
cd ai-assistant-mobile/ios
pod install
```

#### 2.3.4 修改AppDelegate.swift

在`ai-assistant-mobile/ios/Runner/AppDelegate.swift`中添加Firebase初始化：

```swift
import Flutter
import UIKit
import Intents
import UserNotifications
import Firebase  // 添加这行

@main
@objc class AppDelegate: FlutterAppDelegate {

    override func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {

        // 初始化Firebase
        FirebaseApp.configure()  // 添加这行

        let controller = window?.rootViewController as! FlutterViewController

        // 设置通知代理（允许前台显示通知）
        if #available(iOS 10.0, *) {
            UNUserNotificationCenter.current().delegate = self
        }

        // ... 其余代码保持不变

        GeneratedPluginRegistrant.register(with: self)
        return super.application(application, didFinishLaunchingWithOptions: launchOptions)
    }

    // 添加APNs token注册
    override func application(_ application: UIApplication,
                            didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        // 将APNs token传递给Firebase
        Messaging.messaging().apnsToken = deviceToken
    }
}
```

#### 2.3.5 添加推送通知能力

在Xcode中：
1. 选择Runner target
2. 点击"Signing & Capabilities"
3. 点击"+ Capability"
4. 添加"Push Notifications"
5. 添加"Background Modes"，勾选"Remote notifications"

---

## 第三步：Android配置

### 3.1 修改build.gradle配置

#### 3.1.1 项目级build.gradle

在`ai-assistant-mobile/android/build.gradle`中添加：

```gradle
buildscript {
    repositories {
        google()
        mavenCentral()
    }

    dependencies {
        classpath 'com.android.tools.build:gradle:8.1.0'
        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"
        // 添加Google Services插件
        classpath 'com.google.gms:google-services:4.4.0'
    }
}
```

#### 3.1.2 应用级build.gradle.kts

在`ai-assistant-mobile/android/app/build.gradle.kts`末尾添加：

```kotlin
plugins {
    id("com.android.application")
    id("kotlin-android")
    id("dev.flutter.flutter-gradle-plugin")
    id("com.google.gms.google-services")  // 添加这行
}

// ... 其余配置保持不变
```

### 3.2 添加google-services.json

确保`google-services.json`文件在：
```
ai-assistant-mobile/android/app/google-services.json
```

---

## 第四步：Flutter应用集成

### 4.1 安装依赖

```bash
cd ai-assistant-mobile
flutter pub get
```

### 4.2 修改main.dart

在`lib/main.dart`中初始化Firebase：

```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'services/firebase_messaging_service.dart';

// 后台消息处理器（必须在main函数外）
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

### 4.3 在登录后注册设备Token

在用户登录成功后，调用：

```dart
final firebaseMessaging = FirebaseMessagingService();
await firebaseMessaging.registerToken(userToken);
```

### 4.4 在登出时取消注册

在用户登出时，调用：

```dart
final firebaseMessaging = FirebaseMessagingService();
await firebaseMessaging.unregisterToken(userToken);
```

---

## 第五步：服务器端配置

### 5.1 创建数据库表

```bash
mysql -u ai_assistant -p ai_assistant < database_device_tokens.sql
```

### 5.2 添加API端点

将`API_PATCH_DEVICE_TOKEN.py`中的代码添加到`assistant_web.py`的相应位置。

### 5.3 配置Firebase Admin SDK

确保`firebase_config.json`文件在项目根目录，内容格式如下：

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@your-project-id.iam.gserviceaccount.com",
  ...
}
```

---

## 第六步：测试

### 6.1 测试iOS推送

1. 在真机上运行应用（模拟器不支持推送）
2. 登录应用
3. 检查控制台是否显示FCM Token
4. 调用测试API：
   ```bash
   curl -X POST http://47.109.148.176/ai/api/device/test-push \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json"
   ```

### 6.2 测试Android推送

1. 在真机或模拟器上运行应用
2. 登录应用
3. 检查控制台是否显示FCM Token
4. 调用测试API（同上）

### 6.3 测试提醒推送

1. 创建一个提醒（设置为1分钟后）
2. 关闭应用或锁屏
3. 等待提醒时间到达
4. 应该收到推送通知

---

## 常见问题

### iOS推送不工作

1. 确认APNs密钥已正确上传到Firebase
2. 确认在真机上测试（模拟器不支持）
3. 确认推送通知权限已授予
4. 检查Xcode中的Capabilities是否正确配置

### Android推送不工作

1. 确认google-services.json文件位置正确
2. 确认Google Services插件已添加
3. 检查应用是否有通知权限
4. 检查Firebase控制台中的Android应用配置

### Token注册失败

1. 检查服务器API端点是否正确
2. 检查用户认证token是否有效
3. 检查数据库表是否已创建
4. 查看服务器日志

---

## 部署到生产环境

### 服务器端

1. 将所有修改的文件上传到服务器
2. 安装firebase-admin：`pip3 install firebase-admin`
3. 上传firebase_config.json到服务器
4. 重启服务：`sudo supervisorctl restart ai-assistant`

### 移动端

1. iOS: 使用Xcode Archive并上传到App Store
2. Android: 使用`flutter build apk --release`构建发布版本

---

## 安全注意事项

1. **不要**将firebase_config.json提交到git
2. **不要**将GoogleService-Info.plist和google-services.json提交到git
3. 在.gitignore中添加：
   ```
   firebase_config.json
   ios/Runner/GoogleService-Info.plist
   android/app/google-services.json
   ```

---

## 完成！

配置完成后，您的应用将能够：
- ✅ 在app关闭时接收推送通知
- ✅ 在锁屏时显示通知
- ✅ 支持iOS和Android双平台
- ✅ 自动管理设备token
- ✅ 支持多设备推送

如有问题，请查看控制台日志或联系技术支持。
