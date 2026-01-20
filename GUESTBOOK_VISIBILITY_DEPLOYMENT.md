# 留言墙可见范围功能部署指南

## 功能说明

将留言墙从"留言板模式"升级为"动态墙模式"，支持：
1. ✅ 查看自己发布的内容
2. ✅ 查看好友发布的内容（根据可见范围）
3. ✅ 发布时选择可见范围：
   - 所有好友可见
   - 指定好友可见
   - 仅自己可见

## 部署步骤

### 1. 数据库迁移

在服务器上执行SQL迁移脚本：

```bash
# 连接到服务器
ssh root@47.109.148.176

# 进入项目目录
cd /var/www/ai-assistant

# 上传迁移脚本（在本地执行）
scp migrate_guestbook_visibility.sql root@47.109.148.176:/var/www/ai-assistant/

# 在服务器上执行迁移
mysql -u ai_assistant -p ai_assistant < migrate_guestbook_visibility.sql
```

迁移脚本会添加以下字段：
- `mood_tag` - 心情标签
- `bg_color` - 背景颜色
- `image_id` - 关联图片ID
- `position_x`, `position_y`, `rotation` - 便签位置和旋转
- `visibility` - 可见范围（all_friends/specific_friends/private）
- `visible_to_users` - 可见用户ID列表（JSON）

### 2. 更新后端代码

上传修改后的文件：

```bash
# 在本地执行
scp guestbook_manager.py root@47.109.148.176:/var/www/ai-assistant/
scp assistant_web.py root@47.109.148.176:/var/www/ai-assistant/
```

### 3. 更新前端代码

```bash
# 在本地执行
scp social.html root@47.109.148.176:/var/www/ai-assistant/
```

### 4. 重启服务

```bash
# 在服务器上执行
sudo supervisorctl restart ai-assistant

# 检查服务状态
sudo supervisorctl status ai-assistant

# 查看日志（如果有问题）
tail -f /var/log/ai-assistant.log
tail -f /var/log/ai-assistant-error.log
```

## 验证测试

### 测试步骤

1. **登录两个不同的用户账号**（使用不同浏览器或无痕模式）

2. **添加好友关系**
   - 用户A添加用户B为好友
   - 用户B接受好友请求

3. **测试发布功能**

   **用户A发布内容：**
   - 发布一条"所有好友可见"的便签
   - 发布一条"指定好友可见"的便签（选择用户B）
   - 发布一条"仅自己可见"的便签

4. **测试查看功能**

   **用户B查看留言墙：**
   - 应该能看到用户A的"所有好友可见"便签 ✅
   - 应该能看到用户A的"指定好友可见"便签（因为选择了B）✅
   - 不应该看到用户A的"仅自己可见"便签 ❌
   - 能看到自己发布的所有便签 ✅

5. **测试图片功能**
   - 发布带图片的便签
   - 确认图片能正常显示

## 回滚方案

如果部署后出现问题，可以快速回滚：

```bash
# 1. 恢复旧版本代码
cd /var/www/ai-assistant
git checkout HEAD~1 guestbook_manager.py assistant_web.py social.html

# 2. 重启服务
sudo supervisorctl restart ai-assistant

# 3. 数据库回滚（可选，如果需要）
# 注意：这会删除新添加的字段和数据
mysql -u ai_assistant -p ai_assistant <<EOF
ALTER TABLE guestbook_messages
DROP COLUMN IF EXISTS visibility,
DROP COLUMN IF EXISTS visible_to_users,
DROP COLUMN IF EXISTS mood_tag,
DROP COLUMN IF EXISTS bg_color,
DROP COLUMN IF EXISTS image_id,
DROP COLUMN IF EXISTS position_x,
DROP COLUMN IF EXISTS position_y,
DROP COLUMN IF EXISTS rotation;
EOF
```

## 常见问题

### Q1: 迁移脚本执行失败，提示字段已存在

**原因**：数据库中已经有部分字段（如 `image_id`）

**解决**：修改迁移脚本，使用 `ADD COLUMN IF NOT EXISTS` 语法（已包含在脚本中）

### Q2: 查询报错 "Unknown column 'visibility'"

**原因**：数据库迁移未成功执行

**解决**：
```bash
# 检查表结构
mysql -u ai_assistant -p ai_assistant -e "DESCRIBE guestbook_messages;"

# 如果缺少字段，重新执行迁移脚本
mysql -u ai_assistant -p ai_assistant < migrate_guestbook_visibility.sql
```

### Q3: 前端显示"加载中..."但没有内容

**原因**：可能是API返回错误或JavaScript错误

**解决**：
1. 打开浏览器开发者工具（F12）
2. 查看Console标签页的错误信息
3. 查看Network标签页，检查API请求是否成功
4. 查看服务器日志：`tail -f /var/log/ai-assistant-error.log`

### Q4: 好友看不到我发布的内容

**原因**：可能是好友关系未正确建立，或可见范围设置问题

**解决**：
```sql
-- 检查好友关系
SELECT * FROM friendships WHERE (user1_id = 用户A的ID OR user2_id = 用户A的ID) AND status = 'accepted';

-- 检查留言的可见范围
SELECT id, author_id, content, visibility, visible_to_users FROM guestbook_messages WHERE author_id = 用户A的ID;
```

## 性能优化建议

1. **添加索引**（迁移脚本已包含）：
   ```sql
   ALTER TABLE guestbook_messages ADD INDEX idx_visibility (visibility);
   ALTER TABLE guestbook_messages ADD INDEX idx_image_id (image_id);
   ```

2. **定期清理旧数据**：
   ```sql
   -- 删除6个月前的留言（可选）
   DELETE FROM guestbook_messages WHERE created_at < DATE_SUB(NOW(), INTERVAL 6 MONTH);
   ```

3. **监控查询性能**：
   ```sql
   -- 查看慢查询
   SHOW VARIABLES LIKE 'slow_query_log';
   ```

## 后续优化方向

1. **移动端适配**：更新 Flutter 应用的留言墙页面
2. **通知功能**：好友发布新内容时推送通知
3. **评论功能**：支持对便签进行评论
4. **标签功能**：支持给便签添加标签分类
5. **搜索功能**：支持搜索便签内容

## 联系方式

如有问题，请查看：
- 服务器日志：`/var/log/ai-assistant.log`
- 错误日志：`/var/log/ai-assistant-error.log`
- 项目文档：`/var/www/ai-assistant/CLAUDE.md`
