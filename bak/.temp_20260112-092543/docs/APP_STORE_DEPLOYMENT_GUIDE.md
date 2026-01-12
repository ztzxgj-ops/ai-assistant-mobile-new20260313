# App Store上架完整指南 - Assistant AI个人助理

**准确北京时间：2026年1月3日 21时23分**

## 📋 目录

1. [第1步：准备开发证书和配置文件](#第1步准备开发证书和配置文件)
2. [第2步：配置Xcode项目](#第2步配置xcode项目)
3. [第3步：构建和测试](#第3步构建和测试)
4. [第4步：准备App Store资源](#第4步准备app-store资源)
5. [第5步：创建应用记录](#第5步创建应用记录)
6. [第6步：上传应用](#第6步上传应用)
7. [第7步：提交审核](#第7步提交审核)
8. [常见问题排查](#常见问题排查)

---

## 第1步：准备开发证书和配置文件

### 1.1 在Apple Developer账户中创建证书

1. 访问 https://developer.apple.com/account
2. 登录你的Apple开发者账户
3. 在左侧菜单选择 **Certificates, Identifiers & Profiles**
4. 点击 **Certificates**，然后点击 **+** 创建新证书
5. 选择 **iOS Distribution** （用于App Store发布）
6. 按照提示完成证书请求：
   - 打开 **Keychain Access**
   - 菜单：Keychain Access → Certificate Assistant → Request a Certificate from a Certificate Authority
   - 邮箱填写你的Apple开发者账户邮箱
   - 常用名称：随意（如"Assistant Distribution"）
   - 选择"保存到磁盘"并保存.certSigningRequest文件
7. 在Apple Developer网站上传CSR文件
8. 下载获得的.cer文件，双击导入到Keychain

### 1.2 创建App ID (Bundle Identifier)

1. 在Apple Developer账户中，点击 **Identifiers**
2. 点击 **+** 创建新ID
3. 选择 **App IDs**
4. 输入描述：`Assistant AI Personal Assistant`
5. **Bundle ID** 设置为：`com.gaojun.aiassistant`（这很重要，后面要用到）
6. 启用所需的能力（Capabilities）：
   - ✅ Push Notifications（如果要使用推送）
   - ✅ Siri Kit（如果要使用Siri）
7. 点击 **Continue** 和 **Register** 完成

### 1.3 创建配置文件 (Provisioning Profile)

1. 在Apple Developer账户中，点击 **Profiles**
2. 点击 **+** 创建新配置文件
3. 选择 **App Store**
4. 选择刚才创建的App ID：`com.gaojun.aiassistant`
5. 选择刚才创建的Distribution证书
6. 给配置文件命名：`Assistant Distribution Profile`
7. 下载配置文件（.mobileprovision）
8. 双击文件进行安装，或拖入Xcode

---

## 第2步：配置Xcode项目

### 2.1 打开项目

```bash
cd ai-assistant-mobile
open ios/Runner.xcworkspace
```

**重要**：必须打开 `.xcworkspace` 文件，不是 `.xcodeproj`

### 2.2 配置Bundle Identifier和签名

1. 在Xcode中，选择 **Runner** 项目
2. 选择 **Runner** target
3. 点击 **Signing & Capabilities** 选项卡
4. 确保以下设置正确：
   - **Team**：选择你的Apple开发者账户/团队
   - **Bundle Identifier**：`com.gaojun.aiassistant`
   - **Provisioning Profile**：`Assistant Distribution Profile`
5. 对 **RunnerTests** target 也进行相同配置

### 2.3 配置版本号

1. 在Xcode中，选择 **Runner** target
2. 点击 **Build Settings** 选项卡
3. 搜索 "version"，找到以下设置：
   - **Versioning System**：`Apple Generic`
   - **Current Project Version**：`1`（整数，每次提交新版本时递增）
   - **Marketing Version**：`1.0.0`（用户看到的版本号）

或者直接编辑 `pubspec.yaml`：
```yaml
version: 1.0.0+1
```
其中 `+` 前面是用户看到的版本号，后面是构建号

### 2.4 配置应用名称

选择项目，在 **Build Settings** 中搜索 "Product Name"，改为 `Assistant`

或在 `ios/Runner/Info.plist` 中修改：
```xml
<key>CFBundleDisplayName</key>
<string>Assistant</string>
```

---

## 第3步：构建和测试

### 3.1 清理之前的构建

```bash
cd ai-assistant-mobile
flutter clean
rm -rf ios/Pods ios/Podfile.lock
rm -rf ios/.symlinks
```

### 3.2 获取依赖

```bash
flutter pub get
cd ios
pod install --repo-update
cd ..
```

### 3.3 为iOS生成Release构建

```bash
flutter build ios --release
```

这会在 `ios/Runner.xcworkspace` 中生成Release配置。

### 3.4 在Xcode中创建Archive（用于提交）

```bash
open ios/Runner.xcworkspace
```

1. 在Xcode顶部选择 **Product** → **Scheme** → **Runner**
2. 改为 **Release** 配置：在Xcode工具栏中找到配置选择器，改为 **Release**
3. 选择真实设备（不能是模拟器）：比如 **iPhone 15** 或任何连接的真实设备
4. **Product** → **Build** 或按 **Cmd+B** 构建
5. 完成后，**Product** → **Archive**

### 3.5 导出IPA文件

1. 窗口 → Organizer
2. 找到刚才创建的Archive
3. 点击 **Distribute App**
4. 选择 **App Store Connect**
5. 选择 **Upload**
6. 选择签名证书（应该自动选择）
7. 完成导出，Xcode会自动上传到App Store Connect

---

## 第4步：准备App Store资源

### 4.1 应用图标 (Icon)

1. 图标大小：1024×1024px（PNG格式）
2. 图标内容：简洁清晰，代表"AI助理"
3. 不能包含圆角或阴影（iOS会自动处理）

保存位置：`ai-assistant-mobile/ios/Runner/Assets.xcassets/AppIcon.appiconset/`

### 4.2 应用预览截图

需要为以下屏幕尺寸准备截图（英文/中文）：

**iPhone 屏幕（6张）：**
- 5.5" 显示屏（iPhone 6 Plus及更大）
- 4.7" 显示屏（iPhone 6）
- 4" 显示屏（iPhone SE）

**iPad 屏幕（2张，可选）：**
- 12.9" iPad Pro
- 2 Gen iPad Pro

**格式要求：**
- PNG或JPG格式
- 竖屏模式
- 不包含设备边框

**建议截图内容：**
1. **登录界面** - 展示应用入口
2. **对话界面** - 展示AI助理功能
3. **任务管理** - 展示工作计划功能
4. **提醒功能** - 展示提醒事项
5. **用户设置** - 展示个性化功能
6. **头像上传** - 展示文件上传功能

### 4.3 应用预览视频（可选）

- 长度：15-30秒
- 分辨率：1080p 或更高
- 格式：MOV 或 MP4

### 4.4 描述和关键字

**App 名称：**
```
Assistant
```

**副标题：**
```
AI个人生活助理
```

**描述：**
```
Assistant 是一款智能AI个人助理应用，帮助您高效管理生活和工作。

主要功能：
• AI聊天 - 与先进的AI进行自然对话
• 任务管理 - 轻松记录和跟踪工作计划
• 智能提醒 - 不错过任何重要事项
• 语音输入 - 支持语音与AI交互
• 头像上传 - 个性化你的个人资料
• 跨设备同步 - 数据在多个设备间同步

为什么选择Assistant？
✨ 智能化：由先进的AI引擎驱动
🚀 高效率：快速记录任务和提醒
🔒 隐私保护：您的数据安全加密存储
🎯 个性化：根据您的需求定制体验

无论是日常任务管理、工作规划还是个人备忘，Assistant 都是您最可靠的数字助理。

现在下载，开始优化您的生活！
```

**搜索关键字（逗号分隔）：**
```
AI, 人工智能, 助理, 任务管理, 提醒, 生产力, 工作计划, 日程, 笔记, 任务跟踪
```

---

## 第5步：创建应用记录

### 5.1 在App Store Connect中创建应用

1. 访问 https://appstoreconnect.apple.com
2. 登录Apple开发者账户
3. 点击左侧 **App Store Connect** → **我的App**
4. 点击右上角 **+** → **新建App**
5. 选择平台：**iOS**
6. 填写表单：
   - **应用名称**：`Assistant`
   - **套装ID**（Bundle ID）：`com.gaojun.aiassistant`
   - **SKU**：`assistant_2026_01`（唯一标识符，不会显示给用户）
   - **用户访问权限**：`完全访问`
7. 点击 **创建**

### 5.2 填写应用信息

1. 在应用页面，点击 **信息**选项卡
2. 填写**基本信息**：
   - **主类别**：`生产力工具` 或 `工具应用`
   - **副类别**（可选）：`任务管理`
   - **内容等级**：点击 **编辑** 完成问卷（通常全部选"无"）
3. **许可证和隐私**：
   - **隐私政策URL**：上传隐私政策到你的网站，然后填写URL
     ```
     如果还没有网站，可以创建一个简单的页面或使用：
     https://example.com/privacy （需要自己托管）

     临时方案：可以使用免费的GitHub Pages或GitLab Pages
     ```
   - **使用条款URL**（可选）
   - **许可协议**（可选）

### 5.3 配置版本信息

1. 点击 **App Store** 选项卡
2. 点击 **新增版本** → **新的iOS App**
3. 填写版本信息：
   - **版本号**：`1.0.0`（需要与pubspec.yaml中的marketing version一致）
   - **版本发布日期**：`自动发送`（或选择特定日期）
   - **演示视频**（可选）
   - **支持网址**：`https://example.com/support` 或邮箱网址
   - **市场营销网址**（可选）
   - **演示视频**（可选）

4. **运行你的App** 部分：
   - **升级说明**：
     ```
     首个版本发布
     ```
   - **描述**：粘贴上面准备的描述文本
   - **关键字**：粘贴上面准备的关键字
   - **支持网址**：`ynztgj230@outlook.com` 或你的网站支持页面
   - **营销URL**（可选）
   - **隐私政策URL**（必填）

5. **App 预览和屏幕截图**：
   - 点击 **+** 添加屏幕截图
   - 为每个设备尺寸添加6张截图
   - 上传应用图标

### 5.4 应用审核信息

点击 **App Review Information** 选项卡，填写：

- **用户名和密码**：测试账户（如果需要）
  ```
  用户名：test@example.com
  密码：TestPassword123!
  ```
  （如果你的应用不需要登录，可以跳过）

- **备注**：
  ```
  这是一个AI个人助理应用，使用通义千问API进行智能对话。

  登录信息：
  - 用户可以创建新账户或使用测试账户：
    邮箱：test@example.com
    密码：TestPassword123!

  主要功能：
  1. AI对话 - 与AI聊天交流
  2. 任务管理 - 记录和管理工作计划
  3. 提醒功能 - 设置提醒事项
  4. 语音输入 - 使用麦克风输入
  5. 头像上传 - 管理用户资料

  应用使用我们的后端服务器进行数据存储和AI查询。
  后端地址：47.109.148.176/ai/

  感谢审核！
  ```

- **联系方式**：
  ```
  邮箱：ynztgj230@outlook.com
  ```

---

## 第6步：上传应用

### 6.1 使用Xcode自动上传（推荐）

1. 完成 [第3步：构建和测试](#第3步构建和测试) 中的Archive步骤
2. Xcode会自动上传到App Store Connect

### 6.2 使用Transporter应用上传

如果Xcode上传失败，可以使用Apple Transporter：

```bash
# 下载Transporter（通过Mac App Store）
# 或使用命令行工具 altool（已弃用，Apple推荐使用xcrun）

# 使用xcrun上传IPA
xcrun altool --upload-app -f "path/to/app.ipa" \
  -t iOS \
  -u "your-apple-id@example.com" \
  -p "your-app-specific-password"
```

### 6.3 验证上传

1. 返回App Store Connect
2. 点击应用的 **版本1.0** （或你的版本号）
3. 向下滚动到 **构建**部分
4. 应该看到你上传的构建版本
5. 点击 **+** 在 **Build** 部分选择上传的版本

---

## 第7步：提交审核

### 7.1 完整性检查清单

在提交审核前，确保以下信息都已填写：

- ✅ 应用名称、副标题、描述
- ✅ 搜索关键字（最多5个）
- ✅ 6张屏幕截图（每个设备尺寸）
- ✅ 应用图标（1024×1024px）
- ✅ 隐私政策URL
- ✅ 支持网址/邮箱
- ✅ 应用类别
- ✅ 内容等级问卷
- ✅ 构建版本已上传并选中
- ✅ App Review Information 已填写

### 7.2 审核前的自检

1. 确保应用在真实设备上运行良好
2. 检查所有权限提示（麦克风、相机、日历等）
3. 确保网络连接到正确的后端服务器
4. 测试登录、聊天、任务管理等核心功能
5. 确保没有崩溃或性能问题

### 7.3 提交审核

1. 在App Store Connect中，找到应用版本
2. 点击右上角 **提交审核**
3. 如果有提示，勾选相关的 **IDFA** 和 **数据收集** 选项：
   - ❌ **跟踪**：你的应用不跟踪用户（如果不用第三方追踪）
   - ❌ **数据链接到用户**：除非你的应用跟踪用户行为
   - ❌ **第三方广告**：如果没有广告
4. 点击 **提交**

### 7.4 等待审核

审核通常需要 **1-5个工作日**（有时更快）。

你可以在以下位置查看审核状态：
- **Activity** 选项卡中的"构建活动"
- 或在 **App Store Connect** 首页查看状态

---

## 常见问题排查

### Q1：签名失败：Code Signing Error

**错误信息**：`Code signing is required for product type 'Application' in SDK 'iphoneos'`

**解决方案**：
```bash
# 1. 确保有效的开发证书和配置文件
# 2. 在Xcode中重新选择Team
# 3. 清理构建文件
flutter clean
rm -rf ios/Pods ios/Podfile.lock
flutter pub get
cd ios && pod install --repo-update
```

### Q2：Pod依赖错误

**错误信息**：`Could not find SDK path for platform ios`

**解决方案**：
```bash
cd ios
rm Podfile.lock
pod deintegrate
pod install --repo-update
cd ..
flutter pub get
```

### Q3：构建到真实设备失败

**常见原因**：
- 设备未信任开发证书
- Bundle ID不匹配
- Provisioning Profile过期

**解决方案**：
1. 在iPhone上：设置 → 通用 → VPN与设备管理 → 信任开发者证书
2. 检查Xcode中的Bundle ID和Team设置
3. 重新生成Provisioning Profile（Apple Developer中）

### Q4：后端连接失败

**错误信息**：`Failed to connect to 47.109.148.176`

**原因**：
- 网络不可用
- 后端服务器离线
- HTTPS证书问题

**解决方案**：
1. 检查网络连接
2. 启动后端服务器：
   ```bash
   python3 assistant_web.py
   ```
3. 检查服务器日志
4. 如果使用HTTP（不安全），需要在Info.plist中添加允许：
   ```xml
   <key>NSAppTransportSecurity</key>
   <dict>
       <key>NSAllowsArbitraryLoads</key>
       <true/>
   </dict>
   ```

### Q5：隐私政策URL被拒

**错误信息**：`Missing or invalid privacy policy URL`

**解决方案**：
1. 创建一个可访问的隐私政策页面
2. 可以托管在：
   - 自己的网站
   - GitHub Pages（免费）
   - Gitee Pages（国内访问快）
   - Notion 公开页面

3. 在App Store Connect中填写完整的HTTPS URL

### Q6：应用被拒原因常见问题

**最常见的拒绝原因：**

| 问题 | 解决方案 |
|-----|--------|
| 缺少隐私政策 | 添加有效的隐私政策URL |
| 权限不必要 | 移除不使用的权限申请 |
| 后端服务不稳定 | 确保服务器24/7运行 |
| 内容违规 | 检查AI聊天的输出是否有害 |
| 登录问题 | 提供测试账户给审核人员 |

---

## 完整时间表

| 步骤 | 所需时间 |
|-----|--------|
| 准备证书和配置文件 | 30分钟 |
| 配置Xcode项目 | 30分钟 |
| 构建和测试 | 1-2小时 |
| 准备App Store资源（截图、图标等） | 2-3小时 |
| 创建应用记录和填写信息 | 1小时 |
| 上传应用 | 30分钟 |
| 提交审核 | 5分钟 |
| **等待审核（不需要操作）** | **1-5天** |
| 发布应用 | 5分钟 |

**总耗时（你的操作）**：约 6-8 小时分散在几天内

---

## 后续维护

### 版本更新流程

如果以后要更新应用：

1. 修改 `pubspec.yaml` 中的版本号（例如 1.0.1）
2. 执行 `flutter build ios --release`
3. 在Xcode中创建新的Archive
4. 在App Store Connect中创建新版本
5. 上传新的构建
6. 重复审核流程

### 自动化部署（可选）

可以考虑使用CI/CD服务自动化构建和上传：
- **Codemagic** - Flutter官方推荐
- **GitHub Actions** - 与GitHub集成
- **Fastlane** - 命令行自动化

---

## 需要帮助？

如果遇到问题，请：

1. 查看Apple的官方文档：https://developer.apple.com/app-store/submissions/
2. 查看Flutter官方指南：https://flutter.dev/docs/deployment/ios
3. 联系Apple支持：https://developer.apple.com/contact/
4. 邮件：ynztgj230@outlook.com

**祝发布顺利！🚀**
