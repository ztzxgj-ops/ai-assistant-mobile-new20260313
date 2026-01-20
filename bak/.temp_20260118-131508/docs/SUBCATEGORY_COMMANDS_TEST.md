# 子类别快捷命令测试文档

## 功能说明

新增了4个快捷命令，允许用户直接使用子类别名称记录内容，无需前缀"记录"。

## 新增命令

| 命令 | 子类别代码 | 图标 | 说明 |
|------|-----------|------|------|
| 日记 | diary | 📔 | 记录每日日记 |
| 随想 | thought | 💭 | 记录随时想法 |
| 信息 | info | 📌 | 记录重要信息 |
| 学习笔记 | note | 📚 | 记录学习笔记 |

## 使用方法

### 旧方式（仍然支持）
```
记录 日记 今天心情很好
记录 随想 突然想到一个好主意
```

### 新方式（简化）
```
日记 今天心情很好
随想 突然想到一个好主意
信息 重要的账号信息
学习笔记 Python装饰器的用法
```

## 查看记录

### 查看特定类型的记录
```
日记          # 查看最近的日记
随想          # 查看最近的随想
信息          # 查看最近的信息
学习笔记      # 查看最近的学习笔记
```

### 查看所有记录
```
记录          # 查看所有类型的最近记录
```

## 测试用例

### 测试1：添加日记
**输入：** `日记 今天天气不错，心情很好`
**预期：**
- ✅ 已保存日记
- 记录保存到 daily_records 表
- subcategory_id 指向 diary 子类别

### 测试2：添加随想
**输入：** `随想 突然想到可以用AI来管理日程`
**预期：**
- ✅ 已保存随想
- 记录保存到 daily_records 表
- subcategory_id 指向 thought 子类别

### 测试3：查看日记列表
**输入：** `日记`
**预期：**
- 📔 最近的日记：
- 1. 2026-01-14 - 今天天气不错，心情很好
- （如果没有记录则显示：📔 暂无日记）

### 测试4：批量添加（用逗号分隔）
**输入：** `日记 测试1，测试2，测试3`
**预期：**
- 注意：当前实现会将整个内容作为一条记录
- 如需批量添加，需要分别输入

### 测试5：上下文引用不冲突
**场景：** 先输入"工作"显示任务列表，然后输入"日记 今天完成了很多工作"
**预期：**
- 不会被误判为"完成工作任务"
- 正确保存为日记内容

## 技术实现

### 代码修改

1. **command_system.py**
   - 新增 `SubcategoryRecordCommand` 类（320-375行）
   - 在 `CommandRouter._register_commands()` 中注册4个实例（684-687行）

2. **ai_chat_assistant.py**
   - 更新 `check_context_reference()` 中的 command_words 列表（1157行）
   - 添加新命令词：'日记', '随想', '信息', '学习笔记'

### 数据库表

使用现有的 `daily_records` 表：
```sql
CREATE TABLE daily_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(200),
    content TEXT NOT NULL,
    record_date DATE NOT NULL,
    subcategory_id INT,  -- 关联到 subcategories 表
    mood VARCHAR(50),
    weather VARCHAR(50),
    tags VARCHAR(500),
    is_private BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subcategory_id) REFERENCES subcategories(id)
);
```

## 部署步骤

1. 上传修改的文件到服务器
```bash
scp command_system.py root@47.109.148.176:/var/www/ai-assistant/
scp ai_chat_assistant.py root@47.109.148.176:/var/www/ai-assistant/
```

2. 重启服务
```bash
ssh root@47.109.148.176
cd /var/www/ai-assistant/
sudo supervisorctl restart ai-assistant
sudo supervisorctl status ai-assistant
```

3. 查看日志确认启动成功
```bash
tail -f /var/log/ai-assistant.log
```

## 注意事项

1. **命令词优先级**：新命令词会在 `check_context_reference()` 中被识别，避免误判
2. **数据隔离**：所有记录都通过 user_id 隔离，确保多用户数据安全
3. **子类别ID获取**：通过 `_get_subcategory_id()` 方法动态查询，支持用户自定义子类别
4. **向后兼容**：旧的"记录 日记 xxx"格式仍然有效

## 已知限制

1. 当前不支持批量添加（逗号分隔）
2. 查看记录时默认显示最近10条
3. 搜索功能需要使用"记录 搜索 关键词"命令
