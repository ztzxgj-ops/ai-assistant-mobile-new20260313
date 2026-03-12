# 好友提醒功能实现计划（简化版）

## 需求概述

**核心功能**：
1. A给好友B设置提醒（仅限好友关系）
2. 到点后B的app显示提醒通知
3. B点击"确认"按钮即可，无需保存历史
4. 一次性提醒，触发后自动清理

**简化点**：
- ❌ 不需要B同意/拒绝机制
- ❌ 不需要编辑/删除功能
- ❌ 不需要保存提醒历史
- ✅ 只需要：创建 → 触发 → 确认

---

## 1. 数据库设计

### 字段说明

在 `reminders` 表中添加3个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `creator_id` | INT | 创建者ID（NULL或等于user_id表示自己创建） |
| `is_friend_reminder` | TINYINT | 0=自己的提醒，1=好友的提醒 |
| `confirmed` | TINYINT | 接收者是否已确认（0=未确认，1=已确认） |

### 数据逻辑

- **自己的提醒**：`creator_id = user_id, is_friend_reminder = 0`
- **好友提醒**：`creator_id != user_id, is_friend_reminder = 1`
- **已确认的提醒**：`confirmed = 1`（可定期清理）

### 迁移脚本

文件：`migration_friend_reminders_simple.sql`

---

## 2. 后端实现

### 2.1 扩展 ReminderSystemMySQL 类

**文件**：`mysql_manager.py` (第383-580行)

**新增方法**：

#### 1. `add_friend_reminder(creator_id, friend_id, content, remind_time, repeat_type='once')`

```python
def add_friend_reminder(self, creator_id, friend_id, content, remind_time, repeat_type='once'):
    """
    给好友创建提醒

    Args:
        creator_id: 创建者ID
        friend_id: 好友ID（接收者）
        content: 提醒内容
        remind_time: 提醒时间
        repeat_type: 重复类型（默认once）

    Returns:
        {'success': bool, 'message': str, 'reminder_id': int}
    """
    # 1. 验证好友关系
    # 2. 插入提醒记录（user_id=friend_id, creator_id=creator_id, is_friend_reminder=1）
    # 3. 返回结果
```

#### 2. `confirm_friend_reminder(reminder_id, user_id)`

```python
def confirm_friend_reminder(self, reminder_id, user_id):
    """
    确认好友提醒（接收者点击确认按钮）

    Args:
        reminder_id: 提醒ID
        user_id: 当前用户ID（必须是接收者）

    Returns:
        {'success': bool, 'message': str}
    """
    # 1. 验证权限（user_id必须等于reminders.user_id）
    # 2. 更新confirmed=1
    # 3. 返回结果
```

#### 3. `get_unconfirmed_friend_reminders(user_id)`

```python
def get_unconfirmed_friend_reminders(self, user_id):
    """
    获取未确认的好友提醒（用于app显示）

    Args:
        user_id: 当前用户ID

    Returns:
        [{'id', 'creator_id', 'creator_name', 'creator_avatar', 'content', 'remind_time', 'triggered'}]
    """
    # 查询：user_id=user_id AND is_friend_reminder=1 AND confirmed=0
    # JOIN users表获取创建者信息
```

#### 4. `cleanup_confirmed_reminders(days=7)`

```python
def cleanup_confirmed_reminders(self, days=7):
    """
    清理已确认的好友提醒（定期任务）

    Args:
        days: 保留天数（默认7天）

    Returns:
        删除的记录数
    """
    # 删除：confirmed=1 AND is_friend_reminder=1 AND remind_time < NOW() - days
```

#### 5. 修改 `list_reminders(user_id)`

```python
# 修改查询条件，排除已确认的好友提醒
WHERE user_id = %s AND (is_friend_reminder = 0 OR confirmed = 0)
```

---

### 2.2 修改 ReminderScheduler

**文件**：`reminder_scheduler.py`

#### 修改 `_send_reminder()` 方法

```python
def _send_reminder(self, reminder):
    """发送提醒通知"""

    # 判断是否为好友提醒
    if reminder.get('is_friend_reminder') == 1:
        # 查询创建者信息
        creator_id = reminder.get('creator_id')
        creator_info = self._get_user_info(creator_id)

        # 通知标题
        title = f"📢 来自 {creator_info['username']} 的提醒"
        message = reminder['content']

        # 发送通知（桌面+WebSocket）
        self._send_notification(reminder['user_id'], title, message, reminder['id'])
    else:
        # 自己的提醒（原有逻辑）
        title = "📢 任务提醒"
        message = reminder['content']
        self._send_notification(reminder['user_id'], title, message, reminder['id'])

    # 标记triggered=1（不删除，等待用户确认）
    self.reminder_system.mark_triggered(reminder['id'])
```

#### 新增辅助方法

```python
def _get_user_info(self, user_id):
    """获取用户信息"""
    # 查询users表，返回username和avatar_url
```

---

## 3. API接口设计

**文件**：`assistant_web.py`

### 新增API端点（仅3个）

| 方法 | 端点 | 功能 | 权限 |
|------|------|------|------|
| POST | `/api/social/reminders/create` | 给好友创建提醒 | 需认证+好友关系 |
| GET | `/api/social/reminders/unconfirmed` | 获取未确认的好友提醒 | 需认证 |
| POST | `/api/social/reminders/confirm` | 确认好友提醒 | 需认证+接收者权限 |

### 请求/响应示例

#### 1. 创建好友提醒

```json
// POST /api/social/reminders/create
{
  "friend_id": 123,
  "content": "记得明天开会",
  "remind_time": "2026-02-11 14:00:00",
  "repeat_type": "once"
}

// 响应
{
  "success": true,
  "message": "好友提醒已创建",
  "reminder_id": 456
}
```

#### 2. 获取未确认的好友提醒

```json
// GET /api/social/reminders/unconfirmed
{
  "success": true,
  "reminders": [
    {
      "id": 456,
      "creator_id": 123,
      "creator_name": "张三",
      "creator_avatar": "/uploads/avatars/123.jpg",
      "content": "记得明天开会",
      "remind_time": "2026-02-11 14:00",
      "triggered": 1
    }
  ]
}
```

#### 3. 确认好友提醒

```json
// POST /api/social/reminders/confirm
{
  "reminder_id": 456
}

// 响应
{
  "success": true,
  "message": "提醒已确认"
}
```

---

## 4. 业务流程

### 4.1 创建好友提醒

```
用户A选择好友B
  ↓
验证A和B是否为好友（friendships表，status='accepted'）
  ↓
填写提醒内容、时间
  ↓
调用 add_friend_reminder(creator_id=A, friend_id=B, ...)
  ↓
插入数据库：
  - user_id = B（接收者）
  - creator_id = A（创建者）
  - is_friend_reminder = 1
  - confirmed = 0
  ↓
返回成功，提醒进入调度器
```

### 4.2 提醒触发

```
ReminderScheduler 每30秒检查
  ↓
查询 remind_time <= NOW() AND triggered = 0
  ↓
判断 is_friend_reminder 字段
  ↓
如果是好友提醒：
  - 查询 creator_id 对应的用户名
  - 通知标题：「来自 XXX 的提醒」
  ↓
发送通知（桌面+WebSocket）
  ↓
标记 triggered = 1（不删除记录）
```

### 4.3 接收者确认

```
用户B收到通知
  ↓
在app中看到提醒弹窗
  ↓
点击"确认"按钮
  ↓
调用 /api/social/reminders/confirm
  ↓
更新 confirmed = 1
  ↓
提醒从列表中消失
```

### 4.4 定期清理

```
定时任务（每天凌晨）
  ↓
调用 cleanup_confirmed_reminders(days=7)
  ↓
删除：confirmed=1 AND remind_time < NOW() - 7天
  ↓
释放数据库空间
```

---

## 5. 权限控制

### 简化的权限模型

1. **创建权限**：必须是好友关系（查询friendships表）
2. **确认权限**：只有接收者（user_id）可以确认
3. **无需其他权限**：不需要编辑、删除、拒绝等操作

### 边界情况处理

| 场景 | 处理方式 |
|------|----------|
| 好友关系被删除 | 外键级联删除（ON DELETE CASCADE） |
| 用户被拉黑 | 好友关系变为blocked，无法创建新提醒，已有提醒保留 |
| 循环提醒 | 支持（但建议只用once，避免骚扰） |
| 提醒未确认 | 保留在数据库，app持续显示直到确认 |

---

## 6. 前端交互（简要说明）

### 创建入口

1. **好友列表页面**：每个好友旁边显示"设置提醒"按钮
2. **好友详情页面**：顶部操作栏添加"设置提醒"选项

### 提醒显示

1. **通知弹窗**：
   - 标题：「来自 XXX 的提醒」
   - 内容：提醒文本
   - 按钮：「确认」
2. **提醒列表**：
   - 显示未确认的好友提醒
   - 每条提醒显示创建者头像、名称、内容、时间
   - 点击"确认"后从列表移除

---

## 7. 实施步骤

### 步骤1：数据库迁移

```bash
# 本地测试
mysql -u ai_assistant -p ai_assistant < migration_friend_reminders_simple.sql

# 服务器部署
ssh root@47.109.148.176
cd /var/www/ai-assistant
mysql -u ai_assistant -p ai_assistant < migration_friend_reminders_simple.sql
```

### 步骤2：后端开发

1. 修改 `mysql_manager.py`：
   - 添加4个新方法到 ReminderSystemMySQL 类
   - 修改 list_reminders() 方法

2. 修改 `reminder_scheduler.py`：
   - 修改 _send_reminder() 方法
   - 添加 _get_user_info() 辅助方法

### 步骤3：API开发

在 `assistant_web.py` 添加3个新端点：
- `/api/social/reminders/create`
- `/api/social/reminders/unconfirmed`
- `/api/social/reminders/confirm`

### 步骤4：本地测试

```bash
# 启动服务
python3 assistant_web.py

# 测试API（使用curl）
# 见下方测试脚本
```

### 步骤5：部署到服务器

```bash
cd deploy/
sudo bash deploy.sh
sudo supervisorctl restart ai-assistant
```

---

## 8. 测试脚本

```bash
#!/bin/bash

# 获取两个用户的token
TOKEN_A="user_a_token"
TOKEN_B="user_b_token"

# 1. 创建好友提醒
echo "=== 创建好友提醒 ==="
curl -X POST http://localhost:8000/api/social/reminders/create \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{
    "friend_id": 2,
    "content": "记得明天开会",
    "remind_time": "2026-02-11 14:00:00",
    "repeat_type": "once"
  }'

# 2. 查看未确认的提醒
echo -e "\n\n=== 查看未确认的提醒 ==="
curl -H "Authorization: Bearer $TOKEN_B" \
  http://localhost:8000/api/social/reminders/unconfirmed

# 3. 确认提醒
echo -e "\n\n=== 确认提醒 ==="
curl -X POST http://localhost:8000/api/social/reminders/confirm \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{"reminder_id": 456}'

# 4. 再次查看（应该为空）
echo -e "\n\n=== 再次查看（应该为空） ==="
curl -H "Authorization: Bearer $TOKEN_B" \
  http://localhost:8000/api/social/reminders/unconfirmed
```

---

## 9. 关键文件路径

### 需要修改的文件

1. **数据库迁移**：`migration_friend_reminders_simple.sql`（已创建）
2. **后端管理器**：`mysql_manager.py` (第383-580行，ReminderSystemMySQL类)
3. **调度器**：`reminder_scheduler.py` (第161-267行)
4. **API接口**：`assistant_web.py` (添加3个新端点)

### 可复用的现有功能

- **好友关系验证**：`friendship_manager.py` (check_friendship方法)
- **WebSocket推送**：`websocket_server.py` (send_reminder方法)
- **时间解析**：`reminder_scheduler.py` (parse_reminder_time方法)

---

## 10. 优势对比

### 简化版 vs 复杂版

| 特性 | 复杂版 | 简化版 |
|------|--------|--------|
| 数据库字段 | 5个新字段 | 3个新字段 |
| 后端方法 | 7个新方法 | 4个新方法 |
| API端点 | 7个端点 | 3个端点 |
| 权限控制 | 3层验证 | 1层验证 |
| 用户操作 | 查看/编辑/删除/拒绝 | 确认 |
| 开发时间 | ~2天 | ~4小时 |
| 维护成本 | 高 | 低 |

---

## 总结

这个简化版方案：
- ✅ 满足核心需求（好友提醒）
- ✅ 实现简单（3个API，4个方法）
- ✅ 用户体验好（一键确认）
- ✅ 维护成本低（无复杂权限）
- ✅ 性能友好（定期清理历史）

**建议**：先实现这个简化版，如果后续有需求再扩展功能。
