# App Store 上架完整指南

## 前提条件

### 1. Apple Developer 账号
- **费用**：99美元/年
- **注册地址**：https://developer.apple.com/programs/enroll/
- **审核时间**：1-2个工作日

**注册步骤**：
1. 访问 https://developer.apple.com
2. 点击"Account"登录Apple ID
3. 选择"Join the Apple Developer Program"
4. 选择账号类型（个人/公司）
5. 支付99美元年费
6. 等待审核通过

---

## 第一步：准备应用资料

### 1.1 应用基本信息
- **应用名称**：AI个人助理（或 AI Personal Assistant）
- **副标题**：智能对话与任务管理助手
- **Bundle ID**：com.yourdomain.aipersonalassistant（需要唯一）
- **SKU**：ai-personal-assistant-001
- **主要语言**：简体中文

### 1.2 应用描述

**简短描述**（30字以内）：
```
智能AI助理，帮您管理日常任务、提醒事项，支持语音对话和图片识别。
```

**详细描述**（建议）：
```
AI个人助理是一款智能的个人助理应用，集成了先进的AI对话能力，帮助您高效管理日常生活和工作。

【核心功能】
• 智能对话：基于通义千问AI，支持自然语言交互
• 任务管理：快速记录工作计划，设置优先级和截止日期
• 智能提醒：支持定时提醒、循环提醒，不错过重要事项
• 图片识别：上传图片进行AI分析和识别
• 语音输入：支持语音转文字，快速记录想法
• 留言板：与好友分享消息和想法
• 私信功能：一对一私密聊天
• 数据同步：云端存储，多设备同步

【适用场景】
• 工作任务管理和进度跟踪
• 日常事项提醒和备忘
• 快速记录灵感和想法
• 智能问答和信息查询
• 图片内容识别和分析

【隐私保护】
• 所有数据加密存储
• 支持本地数据备份
• 严格的隐私政策保护用户信息

让AI个人助理成为您的智能生活伙伴！
```

### 1.3 关键词（100字符以内，逗号分隔）
```
AI助理,智能助手,任务管理,提醒事项,语音识别,图片识别,个人助理,待办事项,日程管理,智能对话
```

### 1.4 应用分类
- **主要分类**：效率工具（Productivity）
- **次要分类**：工具（Utilities）

### 1.5 年龄分级
- **建议**：4+（适合所有年龄）

---

## 第二步：准备应用截图

### 2.1 所需尺寸
需要准备以下设备的截图：

**iPhone 6.7" Display**（iPhone 15 Pro Max, 14 Pro Max, 13 Pro Max, 12 Pro Max）
- 尺寸：1290 x 2796 像素
- 数量：3-10张

**iPhone 6.5" Display**（iPhone 11 Pro Max, XS Max）
- 尺寸：1242 x 2688 像素
- 数量：3-10张

**iPhone 5.5" Display**（iPhone 8 Plus, 7 Plus, 6s Plus）
- 尺寸：1242 x 2208 像素
- 数量：3-10张

### 2.2 截图内容建议
1. **主界面**：展示AI对话界面
2. **任务管理**：展示工作计划列表
3. **提醒功能**：展示提醒设置界面
4. **图片识别**：展示图片上传和识别结果
5. **语音输入**：展示语音转文字功能

### 2.3 制作截图
```bash
# 使用iOS模拟器截图
# 1. 启动模拟器
open -a Simulator

# 2. 选择设备（iPhone 15 Pro Max）
# 3. 运行应用
cd ai-assistant-mobile
flutter run

# 4. 截图（Command + S）
# 5. 截图保存在桌面
```

---

## 第三步：准备隐私政策和支持页面

### 3.1 隐私政策URL（必需）
需要创建一个隐私政策页面，托管在你的服务器上。

**示例URL**：http://47.109.148.176/ai/privacy-policy.html

**隐私政策内容要点**：
- 收集哪些数据（用户名、邮箱、聊天记录等）
- 如何使用数据（提供服务、改进功能）
- 数据存储位置（云服务器）
- 数据安全措施（加密存储）
- 用户权利（删除账号、导出数据）
- 第三方服务（通义千问AI）

### 3.2 支持URL（可选但建议）
**示例URL**：http://47.109.148.176/ai/support.html

---

## 第四步：配置Xcode项目

### 4.1 打开Xcode项目
```bash
cd ai-assistant-mobile/ios
open Runner.xcworkspace  # 注意：打开.xcworkspace，不是.xcodeproj
```

### 4.2 配置Bundle ID
1. 选择左侧的"Runner"项目
2. 选择"Runner" Target
3. 在"General"标签页中：
   - **Display Name**：AI个人助理
   - **Bundle Identifier**：com.yourdomain.aipersonalassistant（替换为你的域名）
   - **Version**：1.0.0
   - **Build**：1

### 4.3 配置签名
1. 在"Signing & Capabilities"标签页中：
   - 勾选"Automatically manage signing"
   - **Team**：选择你的Apple Developer账号
   - Xcode会自动生成Provisioning Profile

### 4.4 配置应用图标
- 应用图标已通过 `flutter_launcher_icons` 配置
- 位置：`assets/icons/app_icon.png`
- 确保图标是1024x1024像素的PNG文件

---

## 第五步：Archive和上传

### 5.1 选择目标设备
1. 在Xcode顶部工具栏
2. 选择"Any iOS Device (arm64)"

### 5.2 Archive
1. 菜单栏：Product → Archive
2. 等待编译完成（可能需要5-10分钟）
3. 编译成功后会自动打开Organizer窗口

### 5.3 上传到App Store Connect
1. 在Organizer窗口中，选择刚才创建的Archive
2. 点击"Distribute App"
3. 选择"App Store Connect"
4. 选择"Upload"
5. 选择签名选项（自动管理）
6. 点击"Upload"
7. 等待上传完成（可能需要10-30分钟）

---

## 第六步：在App Store Connect创建应用

### 6.1 登录App Store Connect
- 访问：https://appstoreconnect.apple.com
- 使用Apple Developer账号登录

### 6.2 创建新应用
1. 点击"我的App"
2. 点击"+"号 → "新建App"
3. 填写信息：
   - **平台**：iOS
   - **名称**：AI个人助理
   - **主要语言**：简体中文
   - **Bundle ID**：选择刚才配置的Bundle ID
   - **SKU**：ai-personal-assistant-001
   - **用户访问权限**：完全访问权限

### 6.3 填写应用信息
1. **App信息**：
   - 名称、副标题、分类、隐私政策URL

2. **定价与销售范围**：
   - 价格：免费
   - 销售范围：选择国家/地区（中国、美国等）

3. **App隐私**：
   - 填写数据收集和使用情况
   - 根据实际情况选择收集的数据类型

4. **准备提交**：
   - 上传截图（不同尺寸）
   - 填写描述、关键词
   - 选择构建版本（刚才上传的Archive）
   - 填写版本说明
   - 联系信息、演示账号（如需要）

---

## 第七步：提交审核

### 7.1 审核前检查清单
- [ ] 所有必填信息已填写
- [ ] 截图已上传（至少3张，每个尺寸）
- [ ] 隐私政策URL可访问
- [ ] 应用描述清晰准确
- [ ] 构建版本已选择
- [ ] 测试账号已提供（如果应用需要登录）

### 7.2 提交审核
1. 点击"提交以供审核"
2. 回答审核问卷（出口合规、广告标识符等）
3. 确认提交

### 7.3 审核时间
- **通常**：1-3个工作日
- **快速审核**：可申请加急审核（特殊情况）

---

## 常见审核被拒原因及解决方案

### 1. 缺少隐私政策
**解决**：提供有效的隐私政策URL

### 2. 应用崩溃或无法使用
**解决**：充分测试，确保应用稳定

### 3. 功能不完整
**解决**：确保所有宣传的功能都可用

### 4. 需要登录但未提供测试账号
**解决**：在审核信息中提供测试账号和密码

### 5. 使用了私有API
**解决**：检查代码，移除私有API调用

### 6. 元数据与应用内容不符
**解决**：确保描述、截图与实际功能一致

---

## 审核通过后

### 1. 发布应用
- 审核通过后，可以选择"立即发布"或"手动发布"
- 发布后1-2小时内，应用会在App Store上线

### 2. 监控反馈
- 关注用户评论和评分
- 及时回复用户反馈
- 收集问题和改进建议

### 3. 版本更新
- 修复bug或添加新功能后
- 重复Archive和上传流程
- 提交新版本审核

---

## 费用说明

- **Apple Developer账号**：99美元/年
- **应用上架**：免费
- **应用内购买**：苹果抽成30%（如果有）
- **订阅服务**：苹果抽成30%（第一年），15%（第二年起）

---

## 有用的链接

- **Apple Developer**：https://developer.apple.com
- **App Store Connect**：https://appstoreconnect.apple.com
- **App Store审核指南**：https://developer.apple.com/app-store/review/guidelines/
- **人机界面指南**：https://developer.apple.com/design/human-interface-guidelines/
- **App Store截图规范**：https://help.apple.com/app-store-connect/#/devd274dd925

---

## 下一步

1. 注册Apple Developer账号（如果还没有）
2. 准备应用截图和描述
3. 创建隐私政策页面
4. 配置Xcode项目
5. Archive并上传
6. 在App Store Connect创建应用
7. 提交审核

需要我帮你完成哪一步？
