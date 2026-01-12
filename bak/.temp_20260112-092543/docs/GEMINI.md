# GEMINI.md

在开始任何工作之前，请Gemini助理注意以下几点：
1. **工作重心：** 所有修改和修复都应针对已部署到阿里云服务器上的 AI 助理系统 `http://47.109.148.176/ai/` 进行思考和规划，而非仅仅是本地系统。
2. **项目理解：** 请首先阅读 `项目开发进度记录.md` 文稿，以全面了解项目的最新开发情况和进度。
3. **用户对话标识：** 在模拟用户对话时，请使用黄色标记来区分。
4。请用中文对话交流

## 项目概述

这是一个**多用户个人AI助理系统**，提供Web界面的智能秘书功能。系统支持多用户数据隔离，每个用户拥有独立的聊天记录、工作计划、提醒事项和图片管理。

**项目规模：**
- 总代码量：~9,945行Python代码
- 主程序：`assistant_web.py` (5,381行，包含完整HTML/CSS/JS)
- 核心模块：6个Python文件
- 数据库表：7张表（MySQL）

**核心特性：**
- AI对话助手（支持通义千问等OpenAI兼容API）
- 智能混合记忆模式（临时对话 + 永久记录）
- 多用户认证和数据隔离
- 工作计划管理（支持AI自动识别）
- 智能提醒系统（定时调度）
- 图片管理（支持批量上传/删除）
- 相对时间解析（"明天"、"后天"等自然语言）

**部署状态：**
- 本地开发环境：支持JSON文件存储
- 生产环境：`http://47.109.148.176/ai/` (MySQL数据库)

## 项目文件结构

（文件结构请参考 `CLAUDE.md` 或直接使用 `ls -R` 命令获取最新目录结构）

## 快速启动

### 本地开发启动
```bash
# 确保已安装依赖
pip3 install pymysql

# 配置MySQL（如果使用数据库）
# 编辑 mysql_config.json 填入数据库连接信息

# 启动服务器
python3 assistant_web.py
```
服务器运行在 `http://localhost:8000`

### 停止服务器
```bash
pkill -f "python3 assistant_web.py"
```

### 重启服务器（应用更改后）
```bash
pkill -f "python3 assistant_web.py" && python3 assistant_web.py > server.log 2>&1 &
```

### 查看日志
```bash
tail -f server.log
```

## 架构设计

### 三层架构

```
assistant_web.py (Web服务层)
    ↓ 调用
ai_chat_assistant.py (AI助手层)
    ↓ 使用
mysql_manager.py (数据持久化层)
    ↓ 存储
MySQL数据库 (ai_assistant)
```

**架构说明：**
- 本地开发可使用JSON文件存储（通过`personal_assistant.py`）
- 生产环境使用MySQL数据库（通过`mysql_manager.py`）
- 两种存储方式通过统一的接口进行切换

### 核心模块职责

- **`assistant_web.py`**: Web服务层，处理HTTP请求，用户认证，包含前端HTML/CSS/JS。
- **`ai_chat_assistant.py`**: AI助手层，负责AI对话逻辑，智能搜索，API调用。
- **`mysql_manager.py`**: 数据持久化层，管理数据库连接和各类数据（聊天记录、计划、提醒、图片）。
- **`user_manager.py`**: 用户认证，处理注册、登录、Token管理。
- **`reminder_scheduler.py`**: 提醒调度器，后台线程定时检查提醒并发送通知。
- **`notification_service.py`**: 统一通知接口和队列管理。
- **`personal_assistant.py`**: JSON存储备用方案，用于本地开发。

## 数据存储

**生产环境（云服务器）：** 使用MySQL数据库 `ai_assistant`。
**本地开发（可选）：** 使用JSON文件存储。
**配置文件：** `mysql_config.json`, `ai_config.json`, `reminder_config.json`。
**上传文件：** `uploads/images/`, `uploads/avatars/`。

## 用户认证流程

- **登录流程：** 用户登录，后端返回Token，前端存储Token并跳转主页。
- **API认证：** 所有需要用户隔离的API请求必须在HTTP header中包含 `Authorization: Bearer <token>`。
- **前端认证辅助：** `checkLogin()`, `fetchWithAuth()`, `logout()` 等函数。

## 关键API端点

所有API均以JSON格式交互，响应格式：`{"success": true/false, "data": {...}, "message": "..."}`。
主要分为：认证相关、AI对话、聊天记录、工作计划、提醒事项、图片管理、用户信息等模块。
（具体API路径和参数请参考 `CLAUDE.md` 或代码中的 `assistant_web.py`）

## 智能混合记忆模式

系统使用三层记录机制：
1. **临时对话（内存）：** 保留最近5轮对话，不持久化存储。
2. **永久记录（数据库）：** 用户标记为重要的对话，长期保存，支持搜索。
3. **自动清理：** 7天前的非重要记录自动清理。

## 开发注意事项

- **代码修改后必须重启服务器。**
- **数据库存储方式切换：** 可通过修改导入语句在MySQL和JSON存储之间切换（当前配置为MySQL模式）。
- **添加新的数据管理类：** 所有数据管理类必须支持 `user_id` 参数以实现数据隔离。
- **添加新的API端点：** 需要用户认证的API必须通过 `self.get_current_user()` 获取 `user_id`。
- **AI配置：** 在 `ai_config.json` 中配置模型类型、API密钥、API端点等。

## 云服务器部署

**生产环境架构：** `用户浏览器 -> Nginx -> Python应用 -> MySQL数据库`
**部署位置：** `/var/www/ai-assistant`
**进程管理：** 直接运行或Supervisor。
**访问地址：** `http://47.109.148.176/ai/`

## 测试多用户隔离

（测试方法请参考 `CLAUDE.md` 中提供的 `curl` 命令示例）

## 版本历史

项目有多个归档版本，当前版本是在 v1.4 基础上添加了完整的多用户认证和数据隔离功能。

## 常见问题

- 端口被占用
- 查看服务器日志
- 清除所有用户数据
- AI助手无响应
- 移动端适配问题
- Nginx反向代理路径问题
- 数据库连接失败

（详细解决方案请参考 `CLAUDE.md`）

## 重要文档索引

- `deploy/DEPLOYMENT_GUIDE.md` - 完整部署指南
- `deploy/DATABASE_SETUP.md` - 数据库配置详解
- `智能混合模式说明.md` - AI记忆机制说明
- `API路径说明_重要.md` - API路径配置说明
- `快捷命令使用指南.md` - 系统快捷命令
- `批量删除功能说明_*.md` - 批量操作功能
- `图片管理新功能说明_*.md` - 图片功能详解

## 开发工具和调试

- **数据库管理：** `mysqldump` 备份/恢复，`mysql` 命令查询统计。
- **迁移工具：** `migrate_json_to_mysql.py`。
- **日志分析：** `tail`, `grep`, `awk` 等命令。

---

**Gemini助理注意事项：**

- 在进行任何代码修改前，请务必先仔细阅读相关模块的代码，并理解其功能和与其他部分的交互。
- 优先使用项目已有的工具和框架。
- 在提出修改方案时，请清晰地阐述您的思路和理由。
- 在执行对文件系统或代码库有修改的命令前，我会向您解释该命令的目的和潜在影响。
- 请严格遵守现有的代码风格、命名规范和架构模式。
- 在完成任务后，我会提供简要的说明，不会额外总结，除非您要求。