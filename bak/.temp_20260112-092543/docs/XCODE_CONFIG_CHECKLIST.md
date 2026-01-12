# iOS项目Xcode配置检查清单

准确北京时间：2026年1月3日 21时23分

## ✅ 已完成的配置

### Bundle ID 更新
- ✅ `ios/Runner/RunnerProfile.entitlements`：已从 `group.com.example.aiPersonalAssistant` 更新为 `group.com.gaojun.aiassistant`
- ✅ `ios/Runner/Info.plist`：已从 `com.example.aiPersonalAssistant` 更新为 `com.gaojun.aiassistant`

---

## 📋 Xcode项目配置步骤（需要在Xcode中手动完成）

### 步骤1：打开Xcode项目

```bash
cd ai-assistant-mobile
open ios/Runner.xcworkspace
```

**重要**：必须打开 `.xcworkspace` 而不是 `.xcodeproj`

### 步骤2：配置Signing & Capabilities

1. 在Xcode左侧选择 **Runner** 项目
2. 在中间选择 **Runner** target
3. 点击顶部的 **Signing & Capabilities** 选项卡

4. **配置Team和Bundle ID**：
   ```
   Team: 选择你的Apple开发者账户
   Bundle Identifier: com.gaojun.aiassistant
   ```

5. **检查自动签名**：
   ```
   Automatically manage signing: ✅ 勾选
   ```

6. **对RunnerTests target也进行相同配置**

### 步骤3：配置构建版本号

1. 选择 **Runner** target
2. 点击 **Build Settings** 选项卡
3. 搜索 "version"，确保以下值：
   ```
   Current Project Version: 1
   Versioning System: Apple Generic
   Marketing Version: 1.0.0
   ```

或者直接在 `pubspec.yaml` 中配置：
```yaml
version: 1.0.0+1
```

### 步骤4：验证CocoaPods配置

```bash
cd ai-assistant-mobile/ios
pod install --repo-update
cd ..
```

### 步骤5：验证Flutter配置

```bash
flutter pub get
flutter doctor -v
```

---

## 🔧 常见Xcode配置问题

### 问题1：团队(Team)未显示或无法选择

**解决方案**：
1. Xcode → Preferences → Accounts
2. 点击左下角 **+** 添加你的Apple账户
3. 输入Apple ID和密码
4. 等待"Download Manual Profiles"完成
5. 返回项目，重新选择Team

### 问题2：Code Signing Entitlements冲突

**症状**：Entitlements文件冲突

**解决方案**：
1. 在Signing & Capabilities中检查是否有多个entitlements文件
2. 确保 **Signing Certificate** 选中的是最新的分发证书
3. 点击 **+ Capability** 添加所需功能（如Reminders, Calendar等）

### 问题3：Bundle ID不匹配

**症状**：构建失败，说"Bundle ID mismatch"

**解决方案**：
1. 检查所有文件中的Bundle ID一致性：
   ```bash
   grep -r "com.gaojun.aiassistant" ios/
   grep -r "com.example" ios/
   ```
2. 确保三个位置一致：
   - Xcode项目设置
   - Runner/Info.plist
   - Runner/RunnerProfile.entitlements

---

## 📱 设备测试准备

### 在真实设备上运行

```bash
# 查看连接的设备
flutter devices

# 在连接的设备上运行Debug版本
flutter run

# 在特定设备上运行Release版本
flutter run --release -d <device_id>
```

### 信任开发证书（在iPhone上）

1. 插入iPhone到Mac
2. 在iPhone上：**设置** → **通用** → **VPN与设备管理**
3. 找到你的开发证书，点击 **信任**

---

## 🏗️ 构建Release版本

### 使用Flutter CLI

```bash
# 生成Release版本
flutter build ios --release

# 查看构建输出
ls build/ios/iphoneos/
```

### 使用Xcode

1. 打开 `ios/Runner.xcworkspace`
2. 顶部选择 **Product** → **Scheme** → **Runner**
3. 改为 **Release** 配置：工具栏找到配置选择器，改为 **Release**
4. 选择真实设备（不是模拟器）
5. **Product** → **Build** 或按 **Cmd+B**

---

## 📦 创建App Store提交的Archive

### 在Xcode中创建Archive

1. 打开 `ios/Runner.xcworkspace`
2. 顶部选择 **Product** → **Scheme** → **Runner**
3. 选择 **Release** 配置
4. **必须**选择真实设备（不能是模拟器）
5. **Product** → **Archive**

等待Archive完成（5-10分钟）

### 导出IPA

1. 窗口 → **Organizer**（或 **Product** → **Organizer**）
2. 找到你创建的Archive
3. 点击 **Distribute App**
4. 选择 **App Store Connect** → **Upload**
5. 自动完成签名并上传

---

## ✅ 提交前检查清单

- [ ] Bundle ID 已更新为 `com.gaojun.aiassistant`
- [ ] Apple开发者Team已选中
- [ ] Development Certificate 已安装
- [ ] Distribution Certificate 已安装
- [ ] Provisioning Profile 已安装
- [ ] 版本号正确（1.0.0+1）
- [ ] Release构建成功无错误
- [ ] 在真实设备上测试通过
- [ ] Entitlements文件无冲突
- [ ] CocoaPods依赖已更新
- [ ] 应用图标已配置（Asset Catalog中）

---

## 下一步

完成上述配置后，按照 `APP_STORE_DEPLOYMENT_GUIDE.md` 中的 **第3步：构建和测试** 继续。
