# 分类管理系统部署指南

## 概述

新的分类管理系统为AI助理添加了7大类别的结构化管理功能：
1. 工作类 - 任务管理
2. 计划类 - 带时间的计划
3. 财务类 - 收支记录
4. 账号密码 - 敏感信息存储
5. 提醒类 - 定时提醒
6. 文件类 - 文件管理
7. 记录类 - 日记、随想等

## 新增文件

```
/Users/gj/编程/ai助理new/
├── category_system.py              # 类别管理模块
├── command_system.py               # 命令系统基础架构
├── database_category_schema.sql   # 数据库表结构
└── init_category_database.py      # 数据库初始化脚本
```

## 部署步骤

### 1. 上传文件到服务器

```bash
# 在本地执行
scp category_system.py root@47.109.148.176:/var/www/ai-assistant/
scp command_system.py root@47.109.148.176:/var/www/ai-assistant/
scp database_category_schema.sql root@47.109.148.176:/var/www/ai-assistant/
scp init_category_database.py root@47.109.148.176:/var/www/ai-assistant/
scp ai_chat_assistant.py root@47.109.148.176:/var/www/ai-assistant/
```

### 2. 在服务器上初始化数据库

```bash
# SSH登录服务器
ssh root@47.109.148.176

# 进入项目目录
cd /var/www/ai-assistant/

# 执行数据库初始化
python3 init_category_database.py
```

预期输出：
```
📦 开始初始化分类管理系统数据库...
✅ 创建表: categories
✅ 创建表: subcategories
✅ 创建表: work_tasks
✅ 创建表: finance_records
✅ 创建表: account_credentials
✅ 创建表: daily_records
✅ 插入数据: categories
✅ 插入数据: subcategories

✅ 数据库初始化完成！
   成功: XX 条语句
   失败: 0 条语句
```

### 3. 重启服务

```bash
# 重启AI助理服务
sudo supervisorctl restart ai-assistant

# 检查状态
sudo supervisorctl status ai-assistant

# 查看日志
tail -f /var/log/ai-assistant.log
```

## 使用方法

### 查看类别结构

用户输入：
```
类别
```

系统返回：
```
📚 系统类别结构：

💼 工作类 (work)
   记录工作任务，未完成前持续显示，可调整优先级排序
   子类别：
   • 紧急任务 - 需要立即处理的紧急工作
   • 重要任务 - 重要但不紧急的工作
   • 日常任务 - 日常例行工作

📅 计划类 (plan)
   带有时间的工作计划，到期当天8:00提醒
   子类别：
   • 今日计划 - 今天要完成的计划
   • 本周计划 - 本周计划安排
   • 本月计划 - 本月计划安排

💰 财务类 (finance)
   记录日常收支、投资、收益等财务信息
   子类别：
   • 收入 - 各类收入记录
   • 支出 - 日常支出记录
   • 投资 - 投资记录
   • 收益 - 投资收益记录

... (其他类别)
```

### 工作任务管理

```
# 查看未完成任务
工作

# 添加任务（使用快捷命令）
工作: 准备会议材料 明天 高

# 完成任务
工作 完成 1
```

### 财务记录

```
# 查看财务汇总
财务

# 记录收入
财务 收入 5000 工资

# 记录支出
财务 支出 200 午餐
```

### 日常记录

```
# 查看最近记录
记录

# 添加记录
记录: 今天天气不错，心情很好
```

### 帮助命令

```
# 查看所有命令
帮助

# 查看特定命令帮助
帮助 工作
```

## 数据库表说明

### categories（一级类别表）
- 存储7大系统类别
- 系统类别不可删除（is_system=TRUE）

### subcategories（二级类别表）
- 每个一级类别下的子分类
- 支持用户自定义子类别（user_id字段）

### work_tasks（工作任务表）
- 替代原有的work_plans表
- 新增sort_order字段支持用户自定义排序

### finance_records（财务记录表）
- 记录收入、支出、投资、收益
- 支持标签和日期范围查询

### account_credentials（账号密码表）
- 安全存储账号密码（密码加密）
- 查询时需要安全验证

### daily_records（日常记录表）
- 日记、随想、信息等
- 支持全文搜索

## 命令系统架构

```
用户输入
    ↓
CommandRouter (命令路由器)
    ↓
Command 子类 (具体命令实现)
    ↓
Manager 类 (数据库操作)
    ↓
MySQL 数据库
```

### 扩展新命令

在 `command_system.py` 中添加新的 Command 子类：

```python
class MyCommand(Command):
    def __init__(self):
        super().__init__(
            name='我的命令',
            aliases=['my', 'cmd'],
            description='命令描述'
        )

    def execute(self, args, user_id, managers):
        # 实现命令逻辑
        return {'response': '执行结果', 'is_command': True}
```

然后在 `CommandRouter._register_commands()` 中注册：

```python
def _register_commands(self):
    commands = [
        CategoryCommand(),
        WorkCommand(),
        MyCommand(),  # 添加新命令
        # ...
    ]
```

## 注意事项

1. **数据迁移**：现有的 work_plans 表数据需要迁移到 work_tasks 表
2. **密码加密**：account_credentials 表使用简单的base64编码，生产环境建议使用更安全的加密方式
3. **权限控制**：账号密码查询需要通过安全验证
4. **性能优化**：大量数据时考虑添加索引优化查询性能

## 故障排查

### 命令不响应
- 检查 command_system.py 是否正确导入
- 查看日志：`tail -f /var/log/ai-assistant.log`
- 确认命令名称和别名是否正确

### 数据库错误
- 检查表是否创建成功：`SHOW TABLES;`
- 检查表结构：`DESC categories;`
- 查看MySQL错误日志

### 导入错误
- 确认所有新文件都已上传
- 检查文件权限：`ls -l *.py`
- 测试导入：`python3 -c "from command_system import get_command_router"`

## 后续开发计划

1. 完善账号密码管理的安全机制
2. 添加文件上传和管理功能
3. 实现计划类的8:00自动提醒
4. 添加财务统计和图表功能
5. 支持用户自定义类别和子类别
6. 实现数据导出功能
