# 留言墙新消息提示功能 - 测试指南

## 问题诊断

你测试后没有看到红色"留言墙new"标记，可能的原因：

### 1. Flutter应用未重新编译 ⚠️
**最可能的原因！** Flutter应用需要重新编译才能包含新代码。

### 2. 没有新留言
检查是否满足以下条件：
- 你的好友发布了新的留言
- 留言的可见范围设置为"所有好友可见"或"指定好友可见"（且包含你）
- 留言是在你上次查看留言墙之后发布的

### 3. 已经查看过留言墙
如果你已经打开过留言墙页面，系统会自动标记为已读，红色标记会消失。

## 测试步骤

### 步骤1：重新编译Flutter应用

```bash
cd ai-assistant-mobile

# 清理旧的编译文件
flutter clean

# 获取依赖
flutter pub get

# 编译并安装到设备
flutter run -d <device-id>

# 或者构建iOS应用
flutter build ios
```

### 步骤2：重置查看时间（测试用）

如果需要重新测试，可以在云服务器上重置你的查看时间：

```bash
# 登录云服务器
ssh root@47.109.148.176

# 连接数据库
mysql -u ai_assistant -p ai_assistant

# 重置你的查看时间（将 YOUR_USER_ID 替换为你的用户ID）
UPDATE users SET guestbook_last_viewed_at = NULL WHERE id = YOUR_USER_ID;

# 或者设置为一个很早的时间
UPDATE users SET guestbook_last_viewed_at = '2020-01-01 00:00:00' WHERE id = YOUR_USER_ID;

# 退出
exit
```

### 步骤3：让好友发布新留言

1. 让你的好友登录应用
2. 进入"朋友" → "留言墙"
3. 发布一条新留言，选择"所有好友可见"
4. 发布成功

### 步骤4：测试新消息提示

1. **完全关闭你的应用**（从后台也要关闭）
2. 重新打开应用
3. 打开侧边栏（左上角菜单按钮）
4. 查看"朋友"项是否显示红色"留言墙new"标记

### 步骤5：验证标记消失

1. 点击"朋友"进入社交中心
2. 切换到"留言墙"标签
3. 返回主页面
4. 再次打开侧边栏
5. 确认红色标记已消失

## 调试方法

### 方法1：查看Flutter日志

```bash
# 运行应用时查看日志
flutter run -d <device-id>

# 查找以下日志：
# 📬 [MainPage] 新留言检查完成: true (未读数: X)
# 或
# 📬 [MainPage] 新留言检查完成: false (未读数: 0)
```

### 方法2：直接测试API

使用你的token测试API（在Flutter应用中获取token）：

```bash
# 替换 YOUR_TOKEN 为你的实际token
curl -X GET "http://47.109.148.176/ai/api/social/guestbook/unread-count" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 应该返回类似：
# {"success": true, "unread_count": 1}
```

### 方法3：检查数据库

```bash
# 登录云服务器
ssh root@47.109.148.176

# 连接数据库
mysql -u ai_assistant -p ai_assistant

# 查看你的查看时间
SELECT id, username, guestbook_last_viewed_at FROM users WHERE username = 'YOUR_USERNAME';

# 查看好友的留言
SELECT id, author_id, content, created_at, visibility
FROM guestbook_messages
WHERE parent_id IS NULL
ORDER BY created_at DESC
LIMIT 10;

# 查看你的好友列表
SELECT * FROM friendships WHERE user_id = YOUR_USER_ID OR friend_id = YOUR_USER_ID;
```

## 常见问题

### Q1: 编译时报错
**A:** 尝试以下步骤：
```bash
cd ai-assistant-mobile
flutter clean
rm -rf ios/Pods ios/Podfile.lock
cd ios && pod install && cd ..
flutter pub get
flutter run
```

### Q2: 红色标记一直显示
**A:** 检查是否正确调用了 `markGuestbookAsViewed()` 方法。查看 `social_center_page.dart` 第137行。

### Q3: API返回404
**A:** 后端已修复，请确保已重新部署：
```bash
ssh root@47.109.148.176 "supervisorctl status ai-assistant"
```

### Q4: 没有好友怎么测试
**A:**
1. 创建两个测试账号
2. 互相添加为好友
3. 用账号A发布留言
4. 用账号B查看是否有红色标记

## 技术细节

### 新留言的判断逻辑

系统会统计以下留言作为"新留言"：
1. 好友发布的留言（不包括你自己）
2. 顶级留言（不包括回复）
3. 创建时间晚于你上次查看留言墙的时间
4. 可见范围包含你（`all_friends` 或 `specific_friends` 且包含你的ID）

### 相关文件

- **后端**: `assistant_web.py` 第1059-1148行
- **Flutter主页**: `ai-assistant-mobile/lib/main.dart` 第1401-1430行
- **API服务**: `ai-assistant-mobile/lib/services/api_service.dart` 第1776-1792行
- **社交中心**: `ai-assistant-mobile/lib/pages/social_center_page.dart` 第137行

## 联系支持

如果以上方法都无法解决问题，请提供：
1. Flutter日志输出
2. API测试结果
3. 数据库查询结果
4. 你的用户ID和好友ID
