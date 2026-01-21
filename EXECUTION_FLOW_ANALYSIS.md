# 用户输入"工作"的完整执行流程

## 1. 前端流程

### 用户操作
```
用户点击"工作"快捷按钮
    ↓
前端发送消息："工作"
    ↓
消息通过HTTP POST发送到后端
    ↓
POST /api/ai/chat
Content-Type: application/json
{
  "message": "工作"
}
```

---

## 2. 后端流程

### 第一步：接收消息 (assistant_web.py)

```python
# 路由：POST /api/ai/chat
user_id = self.require_auth()  # 获取用户ID
message = data.get('message')  # 获取消息："工作"
```

### 第二步：调用AI助理 (ai_chat_assistant.py)

```python
# 调用 AIAssistant.chat()
result = ai.chat(message, user_id)
```

### 第三步：检查快捷命令 (ai_chat_assistant.py:861)

```python
# 在 chat() 方法中
shortcut_result = self.process_shortcut_command(user_message, user_id)
if shortcut_result:
    return shortcut_result
```

**关键代码位置：** `ai_chat_assistant.py:1856-1892`

```python
def process_shortcut_command(self, user_message, user_id=None):
    message = user_message.strip()

    # 检查是否是"其他"查询命令
    if message == '其他':
        return self._handle_query_other_category(user_id)

    # 检查是否是"保存"或"记录"命令
    save_commands = ['保存', '记录']
    # ... 处理保存命令

    # 检查是否是"工作:"或"工作："命令
    if message.startswith('工作:') or message.startswith('工作：'):
        # 处理工作快捷命令
        return ...

    # 如果都不匹配，返回 None
    return None
```

**重要：** 当用户输入"工作"时，`process_shortcut_command()` 返回 `None`，因为"工作"不匹配任何快捷命令格式。

### 第四步：继续处理（因为快捷命令返回None）

```python
# 因为 shortcut_result 是 None，继续执行
# 进入 get_smart_context() 方法
```

### 第五步：获取智能上下文 (ai_chat_assistant.py:59-132)

```python
def get_smart_context(self, user_message, user_id):
    """构建AI上下文"""

    # 1. 提取关键词
    keywords = self.extract_keywords(user_message)
    # 对于"工作"，关键词 = ['工作']

    # 2. 获取所有工作项
    all_items = self.get_all_work_items(user_id, status_filter=None)

    # 3. 特殊处理：如果用户查询的是"工作"
    if user_message == '工作':
        # 第390行的特殊处理
        relevant_plans = pending_plans  # 获取所有未完成的计划
        print(f"🔍 DEBUG: 触发工作查询特殊处理，返回{len(relevant_plans)}个未完成计划")

    # 4. 构建上下文
    context = """你是AI助理...

    重要规则：
    2. **当用户问"工作"、"当前工作"、"未完成工作"时，必须列出下方的所有未完成计划**

    相关聊天记录(...条):
    ...

    未完成的工作计划（共N个，请用序号列出，格式: 1. 标题）：
    1. 任务1
    2. 任务2
    ...
    """

    return context
```

### 第六步：调用AI API (ai_chat_assistant.py:1100+)

```python
# 使用Qwen API
response = openai.ChatCompletion.create(
    model="qwen-turbo",
    messages=[
        {"role": "system", "content": context},
        {"role": "user", "content": "工作"}
    ],
    temperature=0.5,
    max_tokens=300
)

ai_response = response.choices[0].message.content
```

### 第七步：返回结果

```python
return {
    'response': ai_response,  # AI生成的工作列表
    'detected_plans': [],
    'detected_reminders': [],
    'completed_plans': []
}
```

---

## 3. 完整的执行流程图

```
用户点击"工作"按钮
    ↓
前端发送 POST /api/ai/chat {"message": "工作"}
    ↓
后端接收消息
    ↓
调用 AIAssistant.chat("工作", user_id)
    ↓
检查快捷命令 process_shortcut_command("工作")
    ↓
"工作"不匹配任何快捷命令格式 → 返回 None
    ↓
继续执行 chat() 方法
    ↓
调用 get_smart_context("工作", user_id)
    ↓
提取关键词：['工作']
    ↓
获取所有工作项
    ↓
特殊处理：user_message == '工作'
    ↓
获取所有未完成的计划
    ↓
构建AI上下文（包含所有未完成计划）
    ↓
调用Qwen API
    ↓
AI生成响应（列出所有未完成计划）
    ↓
返回结果给前端
    ↓
前端显示工作列表
```

---

## 4. 关键代码位置

| 功能 | 文件 | 行号 | 说明 |
|------|------|------|------|
| 快捷命令处理 | ai_chat_assistant.py | 1856-1892 | 检查是否是快捷命令 |
| 特殊处理"工作" | ai_chat_assistant.py | 390 | 当user_message == '工作'时 |
| 获取未完成计划 | ai_chat_assistant.py | 391 | relevant_plans = pending_plans |
| 构建上下文 | ai_chat_assistant.py | 407-427 | 构建AI提示词 |
| 调用AI API | ai_chat_assistant.py | 1100+ | 调用Qwen API |

---

## 5. 为什么"其他"不工作

现在我们可以看到问题了：

### 当用户输入"其他"时：

```python
# process_shortcut_command() 中
if message == '其他':
    return self._handle_query_other_category(user_id)
```

✅ **这个工作正常** - 返回查询结果

### 但是在web版本中：

web版本可能没有调用 `process_shortcut_command()` 方法，或者有不同的处理逻辑。

---

## 6. 解决方案

需要检查web版本中是否有以下代码：

```python
# 在 assistant_web.py 中的 /api/ai/chat 处理中
shortcut_result = self.ai.process_shortcut_command(user_message, user_id)
if shortcut_result:
    return shortcut_result
```

如果web版本没有这个调用，那就是问题所在！

---

## 总结

**"工作"的执行流程：**

1. 用户点击"工作"按钮
2. 前端发送消息到后端
3. 后端调用 `process_shortcut_command()`
4. "工作"不匹配快捷命令格式 → 返回 None
5. 继续执行 `chat()` 方法
6. 特殊处理：检查 `user_message == '工作'`
7. 获取所有未完成计划
8. 构建AI上下文
9. 调用AI API
10. 返回工作列表

**"其他"应该的执行流程：**

1. 用户点击"其他"按钮
2. 前端发送消息到后端
3. 后端调用 `process_shortcut_command()`
4. "其他"匹配查询命令 → 调用 `_handle_query_other_category()`
5. 查询"其他类"所有数据
6. 返回查询结果

**问题：** web版本可能没有正确调用 `process_shortcut_command()` 方法！
