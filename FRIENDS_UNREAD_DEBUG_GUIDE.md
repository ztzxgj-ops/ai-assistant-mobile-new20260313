# 好友列表未读消息徽章调试指南

## 问题描述
抽屉菜单"朋友"旁有合计数字显示，但点击"朋友"后，好友头像上没有显示未读消息数字。

## 调试步骤

### 1. 重新编译应用（必须）

```bash
cd ai-assistant-mobile

# 清理旧文件
flutter clean

# 获取依赖
flutter pub get

# 编译并运行，查看日志
flutter run -d <device-id>
```

### 2. 查看调试日志

运行应用后，进入"朋友"页面，查找以下日志：

```
🔍 [FriendsPage] 会话列表: [...]
🔍 [FriendsPage] 好友 X 未读数: Y
🔍 [FriendsPage] 好友 XXX (ID: X) 未读数: Y
🔍 [FriendsPage.build] 渲染好友: XXX, unread_count: Y
```

### 3. 检查点

#### 检查点1：会话列表是否正确
查看日志中的"会话列表"，确认：
- 是否有数据
- 每个会话是否包含 `friend_id` 和 `unread_count`

**示例正确输出**：
```
🔍 [FriendsPage] 会话列表: [
  {friend_id: 2, friend_name: '张三', unread_count: 3, ...},
  {friend_id: 3, friend_name: '李四', unread_count: 0, ...}
]
```

#### 检查点2：未读数是否正确映射
查看日志中的"好友 X 未读数: Y"，确认：
- friend_id 是否正确
- unread_count 是否正确

#### 检查点3：好友数据是否包含未读数
查看日志中的"好友 XXX (ID: X) 未读数: Y"，确认：
- 每个好友是否都有 unread_count 字段
- unread_count 的值是否正确

#### 检查点4：UI是否正确渲染
查看日志中的"渲染好友: XXX, unread_count: Y"，确认：
- unread_count 是否有值
- 如果有值但UI不显示，说明是UI渲染问题

### 4. 可能的问题和解决方案

#### 问题1：会话列表为空
**原因**：后端API没有返回会话数据
**解决**：检查后端 `/api/social/messages/conversations` API

#### 问题2：friend_id 不匹配
**原因**：好友列表的 friend_id 和会话列表的 friend_id 不一致
**解决**：检查数据结构，可能需要调整映射逻辑

**当前逻辑**：
```dart
final friendId = friend['friend_id'] ?? friend['id'];
```

可能需要改为：
```dart
final friendId = friend['id'] ?? friend['friend_id'];
```

#### 问题3：unread_count 为 0
**原因**：后端返回的未读数为0，或者映射失败
**解决**：
1. 检查后端是否正确统计未读数
2. 让好友发送消息后再测试

#### 问题4：UI条件判断问题
**当前条件**：
```dart
if (friend['unread_count'] != null && friend['unread_count'] > 0)
```

可能需要改为：
```dart
if (friend['unread_count'] != null && friend['unread_count'] is int && friend['unread_count'] > 0)
```

### 5. 手动测试API

使用curl测试后端API：

```bash
# 获取会话列表
curl -X GET "http://47.109.148.176/ai/api/social/messages/conversations" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 获取好友列表
curl -X GET "http://47.109.148.176/ai/api/social/friends/list" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

对比两个API返回的数据结构，确认：
- 好友列表中的ID字段名（friend_id 还是 id）
- 会话列表中的好友ID字段名（friend_id 还是其他）

### 6. 临时解决方案

如果调试后发现是ID映射问题，可以尝试修改代码：

```dart
// 在 _loadFriends 方法中
for (var friend in friends) {
  // 尝试多种可能的ID字段
  final friendId = friend['friend_id'] ?? friend['id'] ?? friend['user_id'];
  friend['unread_count'] = unreadCountMap[friendId] ?? 0;

  // 强制转换为int类型
  if (friend['unread_count'] is! int) {
    friend['unread_count'] = int.tryParse(friend['unread_count'].toString()) ?? 0;
  }
}
```

### 7. 预期结果

正确运行后，应该看到：
1. 日志显示每个好友的未读数
2. 好友列表中，有未读消息的好友右侧显示红色数字徽章
3. 点击好友进入聊天后，返回好友列表，徽章消失

## 常见问题

### Q1: 日志显示 unread_count 有值，但UI不显示
**A**: 检查数据类型，可能是字符串而不是数字

### Q2: 会话列表为空
**A**: 可能是没有聊天记录，让好友先发送消息

### Q3: friend_id 为 null
**A**: 检查好友列表API返回的数据结构，可能字段名不同

## 下一步

根据日志输出，我们可以确定具体问题并修复。请运行应用后提供日志输出。
