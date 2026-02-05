# Firebase 配置文件获取指南

本指南将帮助您从 Firebase Console 获取所有必要的配置文件。

---

## 📋 需要获取的文件清单

1. **GoogleService-Info.plist** - iOS 配置文件
2. **google-services.json** - Android 配置文件
3. **firebase_config.json** - 服务器端配置文件（服务账号密钥）

---

## 🚀 步骤一：创建 Firebase 项目

### 1.1 访问 Firebase Console

打开浏览器，访问：https://console.firebase.google.com/

### 1.2 创建新项目或选择现有项目

1. 点击 **"添加项目"** 或选择现有项目
2. 输入项目名称（例如：ai-assistant）
3. 选择是否启用 Google Analytics（可选）
4. 点击 **"创建项目"**
5. 等待项目创建完成

---

## 📱 步骤二：添加 iOS 应用

### 2.1 在项目中添加 iOS 应用

1. 在 Firebase 项目主页，点击 **iOS 图标** 或 **"添加应用"** → **iOS**
2. 填写应用信息：
   - **iOS Bundle ID**: `com.gaojun.wangleme`
   - **应用昵称**（可选）: AI Assistant iOS
   - **App Store ID**（可选）: 留空
3. 点击 **"注册应用"**

### 2.2 下载 GoogleService-Info.plist

1. 在下一步中，点击 **"下载 GoogleService-Info.plist"**
2. 保存文件到本地
3. **重要**: 将文件放置到以下位置：
   ```
   /Users/gj/编程/ai助理new/ai-assistant-mobile/ios/Runner/GoogleService-Info.plist
   ```

### 2.3 在 Xcode 中添加配置文件

1. 打开终端，执行：
   ```bash
   cd /Users/gj/编程/ai助理new/ai-assistant-mobile/ios
   open Runner.xcworkspace
   ```

2. 在 Xcode 中：
   - 右键点击 **Runner** 文件夹
   - 选择 **"Add Files to Runner..."**
   - 选择刚才下载的 **GoogleService-Info.plist**
   - ✅ 勾选 **"Copy items if needed"**
   - ✅ 勾选 **"Add to targets: Runner"**
   - 点击 **"Add"**

3. 验证文件已添加：
   - 在 Xcode 左侧文件树中应该能看到 GoogleService-Info.plist
   - 点击文件，右侧 **Target Membership** 应该勾选了 Runner

### 2.4 配置 iOS 推送通知（APNs）

#### 2.4.1 创建 APNs 密钥

1. 访问 Apple Developer：https://developer.apple.com/account/resources/authkeys/list
2. 登录您的 Apple Developer 账号
3. 点击 **"+"** 创建新密钥
4. 填写信息：
   - **Key Name**: Firebase Push Notifications
   - ✅ 勾选 **"Apple Push Notifications service (APNs)"**
5. 点击 **"Continue"** → **"Register"**
6. **下载 .p8 文件**（只能下载一次，请妥善保存）
7. 记录以下信息：
   - **Key ID**: 例如 ABC123DEFG
   - **Team ID**: 在页面右上角，例如 XYZ987HIJK

#### 2.4.2 在 Firebase 中上传 APNs 密钥

1. 返回 Firebase Console
2. 进入 **项目设置** → **Cloud Messaging** 标签
3. 找到 **"Apple 应用配置"** 部分
4. 点击 **"上传"** 按钮
5. 填写信息：
   - **APNs 身份验证密钥**: 上传刚才下载的 .p8 文件
   - **密钥 ID**: 输入记录的 Key ID
   - **团队 ID**: 输入记录的 Team ID
6. 点击 **"上传"**

#### 2.4.3 在 Xcode 中启用推送功能

1. 在 Xcode 中选择 **Runner** target
2. 点击 **"Signing & Capabilities"** 标签
3. 点击 **"+ Capability"**
4. 添加 **"Push Notifications"**
5. 再次点击 **"+ Capability"**
6. 添加 **"Background Modes"**
7. 在 Background Modes 中勾选：
   - ✅ **Remote notifications**

---

## 🤖 步骤三：添加 Android 应用

### 3.1 在项目中添加 Android 应用

1. 在 Firebase 项目主页，点击 **Android 图标** 或 **"添加应用"** → **Android**
2. 填写应用信息：
   - **Android 软件包名称**: `com.example.ai_personal_assistant`
   - **应用昵称**（可选）: AI Assistant Android
   - **调试签名证书 SHA-1**（可选）: 留空
3. 点击 **"注册应用"**

### 3.2 下载 google-services.json

1. 在下一步中，点击 **"下载 google-services.json"**
2. 保存文件到本地
3. **重要**: 将文件放置到以下位置：
   ```
   /Users/gj/编程/ai助理new/ai-assistant-mobile/android/app/google-services.json
   ```

### 3.3 验证文件位置

确认文件在正确的位置：
```bash
ls -la /Users/gj/编程/ai助理new/ai-assistant-mobile/android/app/google-services.json
```

---

## 🖥️ 步骤四：获取服务器端配置文件

### 4.1 生成服务账号密钥

1. 在 Firebase Console 中，点击左上角 **齿轮图标** → **项目设置**
2. 点击 **"服务账号"** 标签
3. 选择 **"Firebase Admin SDK"**
4. 点击 **"生成新的私钥"** 按钮
5. 在弹出的对话框中，点击 **"生成密钥"**
6. 会自动下载一个 JSON 文件（例如：ai-assistant-xxxxx-firebase-adminsdk-xxxxx.json）

### 4.2 重命名并放置文件

1. 将下载的 JSON 文件重命名为 `firebase_config.json`
2. 放置到项目根目录：
   ```
   /Users/gj/编程/ai助理new/firebase_config.json
   ```

### 4.3 验证文件内容

打开 firebase_config.json，确认包含以下字段：
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

### 4.4 设置文件权限（重要）

```bash
chmod 600 /Users/gj/编程/ai助理new/firebase_config.json
```

---

## ✅ 步骤五：验证配置

### 5.1 检查文件是否都已就位

运行检查脚本：
```bash
cd /Users/gj/编程/ai助理new
./test_fcm_local.sh
```

应该看到：
- ✅ firebase_config.json 存在
- ✅ GoogleService-Info.plist 存在（在 Xcode 项目中）
- ✅ google-services.json 存在

### 5.2 iOS 配置验证

```bash
cd ai-assistant-mobile/ios
pod install
```

应该看到 Firebase 相关的 pods 被安装。

### 5.3 Android 配置验证

```bash
cd ai-assistant-mobile
flutter clean
flutter pub get
```

应该没有错误。

---

## 📝 配置文件位置总结

| 文件名 | 位置 | 用途 |
|--------|------|------|
| GoogleService-Info.plist | ai-assistant-mobile/ios/Runner/ | iOS 应用配置 |
| google-services.json | ai-assistant-mobile/android/app/ | Android 应用配置 |
| firebase_config.json | 项目根目录 | 服务器端配置 |

---

## 🔒 安全注意事项

1. **不要提交配置文件到 Git**
   - 这些文件已添加到 .gitignore
   - 包含敏感信息，不应公开

2. **服务器文件权限**
   ```bash
   chmod 600 firebase_config.json
   ```

3. **备份配置文件**
   - 将配置文件保存到安全的地方
   - APNs .p8 文件只能下载一次

---

## ❓ 常见问题

### Q1: 找不到 Bundle ID 或 Package Name

**iOS Bundle ID**:
- 在 Xcode 中打开项目
- 选择 Runner target
- 在 General 标签中查看 Bundle Identifier
- 应该是：`com.gaojun.wangleme`

**Android Package Name**:
- 查看 `android/app/build.gradle.kts`
- 找到 `applicationId`
- 应该是：`com.example.ai_personal_assistant`

### Q2: APNs 密钥上传失败

确认：
- .p8 文件格式正确
- Key ID 和 Team ID 输入正确
- Apple Developer 账号有效

### Q3: google-services.json 下载后找不到

- 在 Firebase Console 项目设置中
- 找到对应的 Android 应用
- 点击 google-services.json 图标重新下载

### Q4: 服务账号密钥下载后是什么格式？

- 应该是 JSON 格式
- 文件名类似：`projectname-xxxxx-firebase-adminsdk-xxxxx-xxxxxxxxxx.json`
- 重命名为 `firebase_config.json`

---

## 🎯 下一步

配置文件获取完成后：

1. **运行本地测试**
   ```bash
   ./test_fcm_local.sh
   ```

2. **安装 iOS 依赖**
   ```bash
   cd ai-assistant-mobile/ios
   pod install
   ```

3. **部署到服务器**
   ```bash
   cd /Users/gj/编程/ai助理new
   ./deploy_fcm_push.sh
   ```

4. **在真机上测试**
   - 按照 FCM_PUSH_TEST_GUIDE.md 进行测试

---

## 📞 需要帮助？

如果遇到问题：
1. 查看 CONFIGURATION_CHECKLIST.md
2. 查看 FCM_PUSH_TEST_GUIDE.md 的故障排查部分
3. 检查 Firebase Console 的日志

---

**配置完成后，请运行 `./test_fcm_local.sh` 验证所有文件是否就位！**
