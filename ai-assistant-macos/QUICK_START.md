# 快速开始

## 🚀 打开应用

### 方式 1：直接打开 Xcode 项目

```bash
cd ai-assistant-macos
open AIAssistant.xcodeproj
```

### 方式 2：使用命令行

```bash
cd ai-assistant-macos
xcodebuild -scheme AIAssistant -configuration Debug
```

## 🎯 运行应用

1. **在 Xcode 中打开项目**
   ```bash
   open AIAssistant.xcodeproj
   ```

2. **选择目标设备**
   - 选择 "My Mac" 或 macOS 模拟器

3. **按 Cmd+R 运行**
   - 或点击 Product → Run

## 🔐 登录

**演示账户：**
- 用户名：`demo`
- 密码：`demo123`

或创建新账户

## 📱 功能演示

### 1. 聊天 (Chat)
- 发送消息给 AI 助理
- 接收 AI 回复

### 2. 计划 (Plans)
- 查看工作计划列表
- 添加新计划
- 标记计划完成

### 3. 提醒 (Reminders)
- 查看所有提醒
- 设置新提醒
- 管理提醒时间

### 4. 设置 (Settings)
- 切换存储模式（云端/本地）
- 查看账户信息
- 退出登录

## 🔧 开发

### 修改代码

所有代码都在 `ContentView.swift` 中：

```swift
// 添加新功能
struct NewView: View {
    var body: some View {
        Text("新功能")
    }
}
```

### 构建发布版本

```bash
xcodebuild -scheme AIAssistant -configuration Release
```

## 📦 应用位置

构建后的应用位置：
```
~/Library/Developer/Xcode/DerivedData/AIAssistant-xxx/Build/Products/Debug/AI个人助理.app
```

## 🐛 调试

### 查看日志

在 Xcode 中打开 Console：
- View → Debug Area → Show Console

### 设置断点

- 点击代码行号左侧
- 按 Cmd+\ 继续执行

## 📚 更多信息

- 项目文档：`README.md`
- 构建指南：`BUILD_GUIDE.md`
- 项目总结：`PROJECT_SUMMARY.md`

---

**现在可以开始使用应用了！** 🎉
