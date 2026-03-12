# 留言墙功能升级部署指南

## 功能说明

本次升级包含两个主要功能：

1. **指定好友可见**：将"仅好友可见"改为"指定好友可见"，用户可以选择特定的好友查看便签
2. **多图片支持**：支持上传最多3张图片（原来只能上传1张）

## 修改的文件

### 前端（Flutter移动应用）
- `ai-assistant-mobile/lib/pages/post_sticky_note_page.dart` - 发布便签页面
- `ai-assistant-mobile/lib/services/api_service.dart` - API服务

### 后端（Python服务器）
- `guestbook_manager.py` - 留言墙管理器
- `assistant_web.py` - Web服务器

### 数据库
- `migrate_guestbook_multi_images.sql` - 数据库迁移脚本

## 部署步骤

### 1. 数据库迁移

在服务器上执行数据库迁移：

```bash
# 上传迁移脚本到服务器
scp migrate_guestbook_multi_images.sql root@47.109.148.176:/var/www/ai-assistant/

# SSH连接到服务器
ssh root@47.109.148.176

# 进入项目目录
cd /var/www/ai-assistant

# 执行迁移脚本
mysql -u ai_assistant -p ai_assistant < migrate_guestbook_multi_images.sql
# 密码：ai_assistant_2024

# 验证迁移结果
mysql -u ai_assistant -p ai_assistant -e "DESCRIBE guestbook_messages;" | grep image
```

迁移脚本会添加 `image_ids` 字段（JSON类型），用于存储多张图片的ID列表。

### 2. 更新后端代码

```bash
# 在本地执行，上传修改后的文件
scp guestbook_manager.py root@47.109.148.176:/var/www/ai-assistant/
scp assistant_web.py root@47.109.148.176:/var/www/ai-assistant/
```

### 3. 重启后端服务

```bash
# SSH连接到服务器
ssh root@47.109.148.176

# 重启服务
sudo supervisorctl restart ai-assistant

# 检查服务状态
sudo supervisorctl status ai-assistant

# 查看日志（如果有问题）
tail -f /var/log/ai-assistant.log
tail -f /var/log/ai-assistant-error.log
```

### 4. 编译Flutter应用

```bash
# 在本地执行
cd ai-assistant-mobile

# 清理缓存
flutter clean
flutter pub get

# 编译iOS应用
flutter build ios --release

# 编译完成后，通过Xcode安装到设备
# 1. 打开 ios/Runner.xcworkspace
# 2. 连接iOS设备
# 3. 选择设备作为目标
# 4. 点击运行按钮安装应用
```

## 功能测试

### 测试1：指定好友可见功能

1. **准备测试环境**
   - 登录用户A
   - 确保用户A有至少2个好友（用户B和用户C）

2. **发布便签**
   - 点击"发布便签"
   - 输入内容
   - 选择"指定好友可见"
   - 在弹出的好友列表中，只选择用户B
   - 点击发布

3. **验证可见性**
   - 用户B登录：应该能看到这条便签 ✅
   - 用户C登录：不应该看到这条便签 ❌
   - 用户A自己：应该能看到这条便签 ✅

### 测试2：多图片上传功能

1. **上传单张图片**
   - 点击"添加图片"
   - 选择1张图片
   - 确认图片显示正常
   - 发布便签
   - 验证便签中图片显示正常

2. **上传多张图片**
   - 点击"添加图片"
   - 选择第1张图片，等待上传完成
   - 再次点击"添加图片"
   - 选择第2张图片，等待上传完成
   - 再次点击"添加图片"
   - 选择第3张图片，等待上传完成
   - 确认显示3张图片缩略图
   - 发布便签
   - 验证便签中3张图片都显示正常

3. **删除图片**
   - 添加2张图片
   - 点击第1张图片右上角的删除按钮
   - 确认第1张图片被删除
   - 发布便签
   - 验证只有1张图片

4. **达到上限提示**
   - 添加3张图片
   - 尝试再次点击"添加图片"
   - 应该显示提示："最多只能添加3张图片" ✅

### 测试3：组合功能测试

1. **多图片 + 指定好友可见**
   - 添加3张图片
   - 选择"指定好友可见"
   - 选择特定好友
   - 发布便签
   - 验证：
     - 选中的好友能看到便签和3张图片 ✅
     - 未选中的好友看不到便签 ❌

## 注意事项

1. **数据库迁移**
   - 迁移脚本会保留原有的 `image_id` 字段，确保向后兼容
   - 新的 `image_ids` 字段会自动从 `image_id` 迁移数据

2. **API兼容性**
   - 后端同时支持 `image_id`（单张）和 `image_ids`（多张）参数
   - 旧版本的客户端仍然可以正常工作

3. **图片数量限制**
   - 前端限制最多3张图片
   - 后端目前没有限制，建议后续添加验证

4. **好友选择**
   - 如果选择"指定好友可见"但没有选择任何好友，发布会失败
   - 前端会在发布前验证是否至少选择了1个好友

## 回滚方案

如果部署后出现问题，可以按以下步骤回滚：

```bash
# 1. 恢复后端代码
ssh root@47.109.148.176
cd /var/www/ai-assistant
git checkout HEAD -- guestbook_manager.py assistant_web.py

# 2. 重启服务
sudo supervisorctl restart ai-assistant

# 3. 数据库回滚（如果需要）
# 注意：这会删除 image_ids 字段
mysql -u ai_assistant -p ai_assistant -e "ALTER TABLE guestbook_messages DROP COLUMN image_ids;"
```

## 常见问题

### Q1: 编译Flutter应用时出现错误
A: 尝试以下步骤：
```bash
cd ai-assistant-mobile
flutter clean
rm -rf ios/Pods ios/Podfile.lock
cd ios && pod install && cd ..
flutter pub get
flutter build ios --release
```

### Q2: 图片上传失败
A: 检查：
- 服务器 `uploads/images/` 目录权限
- 图片大小是否超过限制
- 网络连接是否正常

### Q3: 好友选择对话框不显示好友
A: 检查：
- 用户是否有好友
- API `/api/social/friends/list` 是否正常工作
- 网络请求是否成功

## 完成标志

部署成功的标志：
- ✅ 数据库迁移成功，`image_ids` 字段存在
- ✅ 后端服务正常运行
- ✅ Flutter应用编译成功
- ✅ 可以选择指定好友可见
- ✅ 可以上传最多3张图片
- ✅ 所有测试用例通过
