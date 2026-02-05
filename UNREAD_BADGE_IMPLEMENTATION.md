# 对话界面左上角未读消息徽章功能 - 实现说明

## 功能概述

在对话界面左上角的菜单按钮（三个点）旁边显示红色数字徽章，显示朋友模块的未读消息总数（私聊 + 留言墙）。

## 实现内容

### 1. 后端API（已存在）✅
- `/api/social/messages/unread-count` - 获取私聊未读消息数
- `/api/social/guestbook/unread-count` - 获取留言墙未读消息数

### 2. Flutter前端更新

#### 2.1 MainPageState 状态管理
- 添加 `_totalUnreadCount` 状态变量
- 添加 `_updateTotalUnreadCount()` 方法统计总未读数
- 在应用启动和恢复时自动更新未读数

#### 2.2 ApiService 新增方法
- `getUnreadMessagesCount()` - 获取私聊未读消息数

#### 2.3 MainChatPage 显示徽章
- 添加 `unreadCount` 参数
- 在AppBar的leading部分使用Stack布局
- 显示红色圆形徽章，超过99显示"99+"

## 文件修改清单

### Flutter应用
- ✅ `ai-assistant-mobile/lib/main.dart`
  - 第903行：添加 `_totalUnreadCount` 状态变量
  - 第1175-1194行：添加 `_updateTotalUnreadCount()` 方法
  - 第1270行：在应用恢复时更新未读数
  - 第1492-1502行：MainChatPage添加unreadCount参数
  - 第2138-2174行：AppBar显示红色徽章

- ✅ `ai-assistant-mobile/lib/services/api_service.dart`
  - 第1811-1830行：添加 `getUnreadMessagesCount()` 方法

### 后端（无需修改）
- 后端API已存在，无需修改

## 使用说明

### 编译和安装

```bash
cd ai-assistant-mobile

# 清理旧文件
flutter clean

# 获取依赖
flutter pub get

# 编译并运行
flutter run -d <device-id>

# 或者构建iOS应用
flutter build ios
```

### 功能说明

1. **自动更新**：
   - 应用启动时自动检查未读消息
   - 应用从后台恢复时自动更新
   - 从社交中心返回时自动更新

2. **显示规则**：
   - 未读数 = 私聊未读数 + 留言墙未读数
   - 未读数 > 0 时显示红色徽章
   - 未读数 ≤ 99 时显示实际数字
   - 未读数 > 99 时显示"99+"

3. **徽章位置**：
   - 对话界面左上角
   - 菜单按钮（三个点）的右上角
   - 红色圆形背景，白色数字

## 测试步骤

### 测试私聊未读消息

1. 让好友给你发送私聊消息
2. 不要打开私聊页面
3. 返回对话界面
4. 查看左上角是否显示红色数字徽章

### 测试留言墙未读消息

1. 让好友在留言墙发布新留言或回复
2. 不要打开留言墙页面
3. 返回对话界面
4. 查看左上角是否显示红色数字徽章

### 测试合计数字

1. 让好友同时发送私聊消息和留言墙消息
2. 返回对话界面
3. 查看左上角数字是否为两者之和

### 测试徽章消失

1. 打开"朋友"模块
2. 查看私聊和留言墙
3. 返回对话界面
4. 确认红色徽章消失

## 调试方法

### 查看日志

```bash
flutter run -d <device-id>

# 查找以下日志：
# 📊 [MainPage] 总未读消息数: X (留言墙: Y, 私聊: Z)
```

### 手动测试API

```bash
# 测试私聊未读数
curl -X GET "http://47.109.148.176/ai/api/social/messages/unread-count" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 测试留言墙未读数
curl -X GET "http://47.109.148.176/ai/api/social/guestbook/unread-count" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 技术细节

### 徽章样式
```dart
Container(
  padding: const EdgeInsets.all(4),
  decoration: BoxDecoration(
    color: Colors.red,
    shape: BoxShape.circle,
  ),
  constraints: const BoxConstraints(
    minWidth: 18,
    minHeight: 18,
  ),
  child: Text(
    widget.unreadCount > 99 ? '99+' : '${widget.unreadCount}',
    style: const TextStyle(
      color: Colors.white,
      fontSize: 10,
      fontWeight: FontWeight.bold,
    ),
    textAlign: TextAlign.center,
  ),
)
```

### 更新时机
1. 应用启动：`initState` → `_checkNewGuestbookMessages` → `_updateTotalUnreadCount`
2. 应用恢复：`didChangeAppLifecycleState(resumed)` → `_handleAppResumed` → `_updateTotalUnreadCount`
3. 从社交中心返回：`_openSocialPage().then` → `_checkNewGuestbookMessages` → `_updateTotalUnreadCount`

## 常见问题

### Q1: 徽章不显示
**A:** 检查是否有未读消息，查看日志确认API调用是否成功

### Q2: 数字不准确
**A:** 检查后端API返回值，确认私聊和留言墙的未读数是否正确

### Q3: 徽章位置不对
**A:** 调整 `Positioned` 的 `right` 和 `top` 参数

### Q4: 徽章不消失
**A:** 确认查看消息后是否调用了标记已读的API

## 相关文件

- **Flutter主页**: `ai-assistant-mobile/lib/main.dart`
- **API服务**: `ai-assistant-mobile/lib/services/api_service.dart`
- **后端API**: `assistant_web.py` 第950行和第1059行
