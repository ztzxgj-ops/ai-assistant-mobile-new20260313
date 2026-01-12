# App Store上架完整检查清单

**准确北京时间：2026年1月3日 22时51分**

## ✅ 第1阶段：准备工作（已完成）

### 📄 文档准备
- ✅ 隐私政策（Markdown版）- `PRIVACY_POLICY.md`
- ✅ 隐私政策（HTML版）- `privacy_policy.html`
- ✅ App Store上架指南 - `APP_STORE_DEPLOYMENT_GUIDE.md`
- ✅ Xcode配置清单 - `XCODE_CONFIG_CHECKLIST.md`
- ✅ 快速参考卡 - `APP_STORE_QUICK_REFERENCE.md`
- ✅ 资源管理指南 - `APP_STORE_ASSETS_GUIDE.md`

### 🔧 iOS项目配置
- ✅ Bundle ID更新：`com.gaojun.aiassistant`
- ✅ Info.plist更新
- ✅ Entitlements文件更新
- ✅ 权限声明完整（麦克风、相机、日历、提醒）

### 🎨 应用资源
- ✅ 应用图标（1024×1024px）
- ✅ 6张高质量截图（竖屏模式）
- ✅ 应用名称：Assistant
- ✅ 副标题：AI个人生活助理

### 📋 应用信息
- ✅ 应用描述文本
- ✅ 搜索关键字
- ✅ 支持邮箱：ynztgj230@outlook.com
- ✅ 隐私政策URL（待托管）

---

## 📋 第2阶段：Xcode配置（需要手动完成）

### 在Xcode中需要完成的步骤

```
□ 打开 ios/Runner.xcworkspace
□ 选择Runner项目和Runner target
□ 在Signing & Capabilities中：
  □ 选择你的Apple开发者Team
  □ 设置Bundle ID: com.gaojun.aiassistant
  □ 勾选"Automatically manage signing"
□ 对RunnerTests target也进行相同配置
□ 验证Build Settings中的版本号
□ 清理构建文件：flutter clean
□ 获取依赖：flutter pub get
□ 更新CocoaPods：cd ios && pod install --repo-update
```

---

## 🏗️ 第3阶段：构建和测试（需要完成）

### 本地构建
```bash
# 清理
flutter clean
rm -rf ios/Pods ios/Podfile.lock

# 获取依赖
flutter pub get
cd ios && pod install --repo-update && cd ..

# 构建Release版本
flutter build ios --release
```

### 在真实设备上测试
```bash
# 查看连接的设备
flutter devices

# 在设备上运行
flutter run --release -d <device_id>
```

### 测试清单
- [ ] 应用能正常启动
- [ ] 登录功能正常
- [ ] AI对话功能正常
- [ ] 任务管理功能正常
- [ ] 提醒功能正常
- [ ] 语音输入功能正常
- [ ] 后端连接正常（47.109.148.176/ai/）
- [ ] 没有崩溃或错误

---

## 📦 第4阶段：准备证书和配置文件

### Apple Developer中需要完成的步骤

```
□ 登录 https://developer.apple.com/account
□ 创建Distribution证书（用于App Store）
□ 创建App ID: com.gaojun.aiassistant
□ 创建Provisioning Profile（App Store）
□ 下载并安装证书和配置文件
□ 在Xcode中验证证书已安装
```

---

## 🎯 第5阶段：在App Store Connect中创建应用

### 应用基本信息
```
应用名称：Assistant
套件ID（Bundle ID）：com.gaojun.aiassistant
SKU：assistant_2026_01
用户访问权限：完全访问
```

### 应用信息
```
主类别：生产力工具
副类别：任务管理
内容等级：完成问卷（通常全选"无"）
隐私政策URL：https://your-domain.com/privacy
```

### 版本信息
```
版本号：1.0.0
升级说明：首个版本发布
支持网址：ynztgj230@outlook.com
```

---

## 📸 第6阶段：上传资源到App Store Connect

### 应用图标
```
□ 上传1024×1024px的PNG图标
□ 确保图标清晰可见
□ 不包含圆角或阴影
```

### 屏幕截图
```
□ 为每个设备尺寸上传6张截图
□ 所有截图都是竖屏模式
□ 文本清晰可读
□ 展示应用的核心功能
```

### 应用描述
```
□ 填写应用名称：Assistant
□ 填写副标题：AI个人生活助理
□ 填写完整描述（已准备）
□ 填写搜索关键字（已准备）
```

---

## 🚀 第7阶段：构建和上传

### 在Xcode中创建Archive
```bash
□ 打开 ios/Runner.xcworkspace
□ 选择Release配置
□ 选择真实设备（不是模拟器）
□ Product → Archive
□ 等待Archive完成
```

### 导出并上传IPA
```bash
□ Window → Organizer
□ 选择创建的Archive
□ Distribute App → App Store Connect → Upload
□ 自动完成签名和上传
```

### 在App Store Connect中选择构建
```bash
□ 返回App Store Connect
□ 找到应用版本
□ 在Build部分选择上传的构建版本
□ 验证所有信息完整
```

---

## ✅ 第8阶段：提交审核前检查

### 完整性检查
- [ ] 应用名称已填写
- [ ] 副标题已填写
- [ ] 应用描述已填写
- [ ] 搜索关键字已填写（最多5个）
- [ ] 应用图标已上传
- [ ] 6张截图已上传
- [ ] 隐私政策URL已填写
- [ ] 支持网址已填写
- [ ] 应用分类已选择
- [ ] 内容等级已完成
- [ ] 构建版本已选择
- [ ] App Review Information已填写

### 功能检查
- [ ] 应用在真实设备上运行正常
- [ ] 所有权限提示正常显示
- [ ] 后端服务器连接正常
- [ ] 没有崩溃或性能问题
- [ ] 测试账户信息已准备

---

## 📤 第9阶段：提交审核

### 提交步骤
```bash
□ 在App Store Connect中找到应用版本
□ 点击右上角"提交审核"
□ 选择IDFA和数据收集选项
□ 确认所有信息无误
□ 点击"提交"
```

### 审核期间
```bash
□ 等待Apple审核（通常1-5个工作日）
□ 定期检查审核状态
□ 准备应对可能的反馈
□ 保持后端服务器运行
```

---

## 🎉 第10阶段：发布

### 审核通过后
```bash
□ 收到Apple的审核通过通知
□ 在App Store Connect中查看状态
□ 点击"发布此版本"
□ 应用将在App Store上线
```

### 发布后
```bash
□ 验证应用在App Store中可搜索
□ 验证应用可以下载安装
□ 监控用户反馈和评分
□ 准备后续版本更新
```

---

## 📊 进度总结

| 阶段 | 任务 | 状态 | 完成度 |
|-----|------|------|--------|
| 1 | 准备工作 | ✅ 完成 | 100% |
| 2 | Xcode配置 | ⏳ 待完成 | 0% |
| 3 | 构建和测试 | ⏳ 待完成 | 0% |
| 4 | 证书和配置 | ⏳ 待完成 | 0% |
| 5 | 创建应用记录 | ⏳ 待完成 | 0% |
| 6 | 上传资源 | ⏳ 待完成 | 0% |
| 7 | 构建和上传 | ⏳ 待完成 | 0% |
| 8 | 提交前检查 | ⏳ 待完成 | 0% |
| 9 | 提交审核 | ⏳ 待完成 | 0% |
| 10 | 发布 | ⏳ 待完成 | 0% |

**总体进度**：10% 完成

---

## 🎯 下一步建议

### 立即做（今天）
1. 托管隐私政策HTML文件到网站
2. 记下隐私政策的URL
3. 在Xcode中完成Team和签名配置

### 明天做
4. 本地构建Release版本
5. 在真实设备上测试所有功能
6. 在Apple Developer中创建证书和配置文件

### 后天做
7. 在App Store Connect中创建应用记录
8. 上传应用资源（图标、截图、描述）
9. 创建Archive并上传IPA

### 一周内做
10. 提交审核
11. 等待Apple审核
12. 根据反馈修复问题或直接发布

---

## 📞 需要帮助？

- **Xcode配置问题** → 查看 `XCODE_CONFIG_CHECKLIST.md`
- **详细上架流程** → 查看 `APP_STORE_DEPLOYMENT_GUIDE.md`
- **快速参考** → 查看 `APP_STORE_QUICK_REFERENCE.md`
- **资源管理** → 查看 `APP_STORE_ASSETS_GUIDE.md`
- **技术支持** → 邮件 ynztgj230@outlook.com

---

**祝你上架顺利！🚀**
