# 三种搜索模式实现文档

## 概述

实现了完整的三种搜索模式，区分用户查询的意图，提供不同的搜索范围和结果展示。

---

## 搜索模式详解

### 1. 纯"X"查询模式（分类查询）

**触发条件：**
- 用户输入简单关键词（2-10个字符）
- 不包含"相关"或"所有"后缀
- 不包含特殊符号（？、?、吗、呢、：、:）
- 不是已知命令词（工作、计划、财务等）

**搜索范围：**
- 仅搜索 subcategories 表中的子类别名称
- 如果找到匹配的子类别，返回该子类别的所有记录

**返回结果：**
- 该子类别下的所有分类记录（daily_records）
- 不包含聊天记录、留言墙、工作计划等

**示例：**
```
用户输入：ai
系统处理：
  1. 在subcategories中查找名称包含"ai"的子类别
  2. 找到"ai助理"子类别
  3. 返回"ai助理"子类别的所有记录

输出：
📝 最近的ai助理：
1. 清空留言墙测试内容
   2026-01-20
2. 私聊不用表情
   2026-01-20
...
```

---

### 2. "X相关"查询模式（相关信息查询）

**触发条件：**
- 用户输入包含"相关"后缀
- 例如："ai相关"、"留言墙相关"、"工作相关"

**搜索范围：**
- daily_records（日常记录）
- guestbook_messages（留言墙）
- work_plans（工作计划）
- **不包含** messages（聊天记录）

**返回结果：**
- 所有包含关键词的相关信息
- 按数据来源分组显示
- 显示完整的搜索结果（无数量限制）

**示例：**
```
用户输入：留言墙相关
系统处理：
  1. 在subcategories中查找名称包含"留言墙"的子类别
  2. 未找到（因为没有"留言墙"子类别）
  3. 调用_comprehensive_search_related("留言墙", user_id, include_chat=False)
  4. 搜索daily_records、guestbook、work_plans

输出：
🔍 找到 14 条与'留言墙'相关的信息：

📌 ai助理记录（共4条）：
  1. 清空留言墙测试内容
     [2026-01-20]
  2. 留言墙图片点击可放大
     [2026-01-20]
  ...

📌 留言墙（共10条）：
  5. 大家好！😊
     [2026-01-19]
  6. 我好
     [2026-01-19]
  ...
```

---

### 3. "X所有"查询模式（全面查询）

**触发条件：**
- 用户输入包含"所有"后缀
- 例如："ai所有"、"留言墙所有"、"工作所有"

**搜索范围：**
- messages（聊天记录）
- daily_records（日常记录）
- guestbook_messages（留言墙）
- work_plans（工作计划）
- **包含** messages（聊天记录）

**返回结果：**
- 所有包含关键词的信息（包括聊天记录）
- 按数据来源分组显示
- 显示完整的搜索结果（无数量限制）

**示例：**
```
用户输入：留言墙所有
系统处理：
  1. 在subcategories中查找名称包含"留言墙"的子类别
  2. 未找到
  3. 调用_comprehensive_search_related("留言墙", user_id, include_chat=True)
  4. 搜索messages、daily_records、guestbook、work_plans

输出：
🔍 找到 60 条与'留言墙'相关的信息：

📌 聊天记录（共46条）：
  1. 我说过留言墙的功能吗
     [2026-01-20]
  2. 留言墙怎么用
     [2026-01-20]
  ...

📌 ai助理记录（共4条）：
  47. 清空留言墙测试内容
     [2026-01-20]
  ...

📌 留言墙（共10条）：
  51. 大家好！😊
     [2026-01-19]
  ...
```

---

## 实现细节

### 核心方法

#### 1. `chat()` 方法（第758-808行）

**新增逻辑：**
```python
# 检查"X相关"、"X所有"和纯"X"模式
if '相关' in user_message or '所有' in user_message:
    # 处理"X相关"和"X所有"模式
    if '所有' in user_message:
        fuzzy_result = self._fuzzy_match_subcategory(user_message, user_id, include_chat=True)
    else:
        fuzzy_result = self._fuzzy_match_subcategory(user_message, user_id, include_chat=False)
    # ... 处理结果
else:
    # 处理纯"X"模式
    # 检查是否是简单关键词查询
    if not is_command and 2 <= len(stripped_message) <= 10:
        # 在子类别中查找
        # 如果找到，返回该子类别的记录
```

#### 2. `_fuzzy_match_subcategory()` 方法（第1508-1586行）

**参数：**
- `user_message`: 用户输入
- `user_id`: 用户ID
- `include_chat`: 是否包含聊天记录（False="相关"模式，True="所有"模式）

**返回值：**
- 字符串：子类别名称（如"ai助理"）
- 字典：全面搜索结果（包含response、is_comprehensive_search等字段）
- None：无匹配

#### 3. `_comprehensive_search_related()` 方法（第1588-1666行）

**参数：**
- `keyword`: 搜索关键词
- `user_id`: 用户ID
- `include_chat`: 是否包含聊天记录（默认False）

**搜索流程：**
```python
if include_chat:
    # 搜索messages（聊天记录）
    # 搜索daily_records（日常记录）
    # 搜索guestbook_messages（留言墙）
    # 搜索work_plans（工作计划）
else:
    # 跳过messages搜索
    # 搜索daily_records（日常记录）
    # 搜索guestbook_messages（留言墙）
    # 搜索work_plans（工作计划）
```

#### 4. `_format_comprehensive_search_results()` 方法（第1668-1706行）

**功能：** 格式化搜索结果，按类型分组显示

**输出格式：**
```
🔍 找到 X 条与'关键词'相关的信息：

📌 类型1（共X条）：
  1. 内容摘要...
     [日期]
  2. 内容摘要...
     [日期]

📌 类型2（共X条）：
  3. 内容摘要...
     [日期]
```

---

## 搜索流程图

```
用户输入
    ↓
检查是否包含"相关"或"所有"
    ↓
是 → 调用_fuzzy_match_subcategory(include_chat=True/False)
    ↓
    在subcategories中查找
    ↓
    找到 → 返回子类别名称 → 递归调用chat()
    ↓
    未找到 → 调用_comprehensive_search_related(include_chat=True/False)
    ↓
    搜索所有数据表（根据include_chat决定是否搜索messages）
    ↓
    格式化结果 → 返回搜索结果
    ↓
否 → 检查是否是纯"X"模式
    ↓
是 → 在subcategories中查找
    ↓
    找到 → 返回该子类别的记录
    ↓
    未找到 → 继续其他处理逻辑
    ↓
否 → 继续其他处理逻辑
```

---

## 测试清单

### 测试1：纯"X"查询
- [ ] 输入"ai" → 应返回"ai助理"子类别的所有记录
- [ ] 输入"留言墙" → 应提示无记录（因为没有"留言墙"子类别）
- [ ] 输入"财务" → 应返回"财务"子类别的所有记录

### 测试2："X相关"查询
- [ ] 输入"ai相关" → 应返回所有包含"ai"的信息（不包含聊天记录）
- [ ] 输入"留言墙相关" → 应返回所有包含"留言墙"的信息（daily_records + guestbook + work_plans）
- [ ] 输入"xyz相关" → 应提示无相关信息

### 测试3："X所有"查询
- [ ] 输入"ai所有" → 应返回所有包含"ai"的信息（包含聊天记录）
- [ ] 输入"留言墙所有" → 应返回所有包含"留言墙"的信息（messages + daily_records + guestbook + work_plans）
- [ ] 输入"xyz所有" → 应提示无相关信息

### 测试4：搜索结果完整性
- [ ] 验证"X相关"查询不包含聊天记录
- [ ] 验证"X所有"查询包含聊天记录
- [ ] 验证搜索结果显示完整（无数量限制）
- [ ] 验证搜索结果按类型分组显示

### 测试5：多用户隔离
- [ ] 使用不同用户账号测试
- [ ] 确保只显示当前用户的数据

---

## 部署信息

**部署时间：** 2026-01-20

**部署服务器：** 47.109.148.176

**修改文件：**
- ai_chat_assistant.py

**服务重启：** supervisorctl restart ai-assistant

---

## 代码位置参考

| 功能 | 文件 | 行号 |
|------|------|------|
| 三种模式检测 | ai_chat_assistant.py | 758-808 |
| 模糊匹配子类别 | ai_chat_assistant.py | 1508-1586 |
| 全面搜索 | ai_chat_assistant.py | 1588-1666 |
| 搜索日常记录 | ai_chat_assistant.py | 165-191 |
| 搜索留言墙 | ai_chat_assistant.py | 193-227 |
| 格式化结果 | ai_chat_assistant.py | 1668-1706 |

---

## 性能考虑

1. **搜索范围限制：** 每个表的搜索都有LIMIT限制（20条），防止过大的结果集
2. **关键词提取：** 使用正则表达式快速提取关键词
3. **数据库索引：** 确保搜索字段有适当的索引
4. **缓存机制：** 可以考虑缓存常见查询结果

---

## 未来改进

1. **模糊匹配优化：** 支持拼音、同义词等模糊匹配
2. **搜索排序：** 按相关性、时间等维度排序结果
3. **搜索历史：** 记录用户的搜索历史
4. **高级搜索：** 支持日期范围、类型过滤等高级搜索选项
5. **搜索建议：** 当无结果时，提供相似的搜索建议
