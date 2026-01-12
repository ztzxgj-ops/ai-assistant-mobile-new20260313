# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 声音提示规则 (Audio Notification Rules)

**重要：在以下情况必须播放系统提示音以提醒用户查看屏幕**

使用命令: `afplay /System/Library/Sounds/Glass.aiff`

触发场景：
1. ✅ **编程任务完成时** - 代码编写、修改、测试完成后
2. ❓ **需要用户确认时** - 例如有多个方案需要用户选择、需要用户输入信息
3. ⚠️ **遇到重要问题时** - 发现错误、需要额外信息、遇到阻塞问题

实现方式：
```bash
# 在需要提醒用户的时候执行
afplay /System/Library/Sounds/Glass.aiff
```

注意事项：
- 提示音应该在输出关键信息后播放
- 避免过于频繁播放（例如每个小步骤都播放）
- 只在真正需要用户关注时播放

## Project Overview

This is a multi-user AI personal assistant system with intelligent conversation, task management, reminders, and image handling. It uses a custom Python HTTP server with MySQL backend and integrates with Alibaba's Qwen (通义千问) API.

## Development Commands

### Running the Server

```bash
# Start server (binds to port 8000 by default)
python3 assistant_web.py

# Using supervisor (production)
sudo supervisorctl start ai-assistant
sudo supervisorctl restart ai-assistant
sudo supervisorctl status ai-assistant
```

### Database Operations

```bash
# Connect to database
mysql -u ai_assistant -p ai_assistant

# Initialize database schema
mysql -u root -p ai_assistant < database_schema.sql

# Check database structure
mysql -u ai_assistant -p -e "USE ai_assistant; SHOW TABLES;"
```

### Git Version Control

```bash
# Quick commit
./git_commit.sh "commit message"

# Safe update (creates backup tag before major changes)
./git_safe_update.sh "description of changes"

# View history
./git_history.sh [limit]

# Restore to previous version
./git_restore.sh <commit-hash|tag>
```

### Deployment

```bash
# Deploy to production server (47.109.148.176)
cd deploy/
sudo bash deploy.sh

# Manual steps documented in:
# - deploy/DEPLOYMENT_GUIDE.md
# - deploy/DATABASE_SETUP.md
```

## Architecture

### Request Flow

```
Browser Request
    ↓
Nginx (:80) → /ai/ location
    ↓
Python HTTP Server (:8000) - assistant_web.py
    ↓
┌─────────────┬──────────────┬───────────────┐
│ AI Module   │ User Manager │ MySQL Manager │
│ (通义千问)   │ (Auth/Token) │ (Data Layer)  │
└─────────────┴──────────────┴───────────────┘
    ↓
MySQL Database (ai_assistant)
```

### Core Components

**assistant_web.py** (260KB+)
- Custom HTTP request handler extending BaseHTTPRequestHandler
- Routes: `/`, `/login`, `/api/*` (30+ endpoints)
- Token-based authentication via `Authorization: Bearer` header
- All API endpoints require authentication except login/register
- Important: Uses `self.require_auth()` to get user_id and enforce isolation

**ai_chat_assistant.py**
- `AIAssistant` class: Main chat interface
- Two-stage intelligent search: keyword matching → context building → AI query
- Shortcut command parser: `工作:`, `计划:`, `关键词:` (supports both `:` and `：`)
- Auto-extraction from conversation: plans, reminders, completion status
- Relative time parser: "明天", "后天", "下午" → absolute dates

**mysql_manager.py**
- `MySQLManager`: Base connection manager with context manager for cursors
- `MemoryManagerMySQL`: Chat message storage (messages table)
- `WorkPlanManagerMySQL`: Work plans (work_plans table)
- `ReminderSystemMySQL`: Reminders (reminders table)
- `ImageManagerMySQL`: Image uploads (images table)
- `KeywordManager`: Dynamic search keywords (search_keywords table)

**user_manager.py**
- `UserManager`: User registration, login, token management
- Password hashing: SHA256
- Session tokens: 32-byte secure random (secrets.token_urlsafe)
- Token expiry: 7 days from creation
- User data isolation via user_id foreign keys

**reminder_scheduler.py**
- Background thread-based scheduler (check interval: 30 seconds)
- `ReminderScheduler`: Monitors database for due reminders
- Time parser: "明天14:30", "1小时后", "3分钟后"
- Notification delivery via notification_service.py

**notification_service.py**
- Cross-platform system notifications (macOS/Linux/Windows)
- macOS: AppleScript display notification
- Linux: notify-send
- Windows: PowerShell ToastNotification

### Database Schema

7 core tables in `ai_assistant` database:

1. **users** - User accounts (id, username, password_hash, avatar_url, chat_background)
2. **user_sessions** - Session tokens (token, user_id, expires_at)
3. **messages** - Chat history (user_id, role, content, timestamp)
4. **work_plans** - Tasks (user_id, title, content, priority, status, due_date)
5. **reminders** - Scheduled reminders (user_id, content, remind_time, triggered)
6. **images** - Uploaded files (user_id, filename, file_path, tags)
7. **search_keywords** - Custom search keywords (keyword, source, user_id)

All tables use `user_id` foreign key to `users(id)` with `ON DELETE CASCADE` for data isolation.

### Key Data Isolation Pattern

Every data access MUST include user_id filtering:

```python
# CORRECT - with user_id isolation
plans = planner.list_plans(user_id=user_id)
messages = memory.get_recent_messages(limit=10, user_id=user_id)

# INCORRECT - security vulnerability, returns all users' data
plans = planner.list_plans()  # ❌ Never do this
```

In `assistant_web.py`, always use:
```python
user_id = self.require_auth()  # Returns user_id or sends 401
if user_id is None:
    return  # Already sent error response
```

### Relative Time Parsing

The system intelligently converts natural language to dates:

- "明天" → tomorrow's date (YYYY-MM-DD)
- "后天" → day after tomorrow
- "下午" / "晚上" → today's date (time context)
- "明早" → smart: if current hour < 6: today, else tomorrow
- "3天后" → current date + 3 days

Handled in:
- `ai_chat_assistant.py`: `parse_relative_time()`
- `assistant_web.py`: `parse_relative_time()` (duplicated)
- `reminder_scheduler.py`: `parse_reminder_time()`

### Shortcut Command System

Users can quickly record data via special prefixes:

**工作:** (Work record)
```
Input: "工作: 下午准备管委会会议材料"
Action:
  1. Saves to messages table
  2. Auto-creates work plan with parsed time
  3. Extracts time phrases ("下午") and includes in title
```

**计划:** (Plan)
```
Input: "计划: 完成报表 (明天) 高"
Action: Parses and creates work_plan entry
```

**关键词:** (Keyword management)
```
Input: "关键词: 添加 工资,奖金"
Input: "关键词: 删除 工资"
Input: "关键词: 查看"
Action: Manages search_keywords table (system/global/user scopes)
```

### AI Integration

Configuration in `ai_config.json`:
```json
{
  "model_type": "openai",
  "api_key": "sk-...",
  "model_name": "qwen-turbo",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
}
```

API call flow:
1. User message → `AIAssistant.chat()`
2. Build smart context via `get_smart_context()`: searches recent messages + plans matching keywords
3. Send to Qwen API with context as system message
4. Parse response for auto-detected plans/reminders
5. Return structured response: `{response, detected_plans, detected_reminders, completed_plans}`

### Auto-Detection Features

**Plan Detection** (`extract_plans_from_message`):
- Looks for action words: "做", "完成", "提交", "处理"
- Extracts time references: "明天", "下周", "月底"
- Priority keywords: "重要", "紧急", "优先"

**Reminder Detection** (`extract_and_create_reminders`):
- Keywords: "提醒", "通知", "叫我"
- Time patterns: "N分钟后", "明天X:XX"
- Auto-creates reminder in database + scheduler

**Completion Detection** (`detect_and_complete_plans`):
- Matches: "第3项完成了", "完成第3项", "做完xxx"
- Updates status to 'completed'
- Deletes related chat history to avoid stale context

## Configuration Files

### mysql_config.json
```json
{
  "host": "localhost",
  "user": "ai_assistant",
  "password": "CHANGE_THIS_PASSWORD",
  "database": "ai_assistant",
  "charset": "utf8mb4"
}
```

### ai_config.json
```json
{
  "model_type": "openai",  // or "simple" for rule-based fallback
  "api_key": "sk-...",
  "model_name": "qwen-turbo",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "temperature": 0.5,
  "max_tokens": 300
}
```

Both files are git-ignored and must be manually created on deployment.

## Common Gotchas

### Port 8000 Already in Use
```bash
# Find and kill the process
lsof -i :8000
kill -9 <PID>
```

### Database Connection Errors
- Check mysql_config.json exists and has correct credentials
- Verify MySQL service is running: `systemctl status mysql`
- Test connection: `mysql -u ai_assistant -p ai_assistant`

### Token Expiration Issues
- Tokens expire after 7 days
- Frontend auto-redirects to login on 401
- Clean expired sessions: `DELETE FROM user_sessions WHERE expires_at < NOW()`

### File Upload Failures
- uploads/ directory must be writable by www-data user
- Permissions: `chmod 775 uploads/ && chown www-data:www-data uploads/`
- Max upload size controlled by `client_max_body_size 10M` in nginx

### Relative Time Edge Cases
- "明早" at 5:30 AM → today (current_hour < 6)
- "明早" at 8:00 AM → tomorrow
- "下午" / "晚上" without explicit date → uses current date
- Empty deadline → defaults to current date

## Multi-User Isolation Critical Points

1. **Never query without user_id** in multi-user tables (messages, work_plans, reminders, images)
2. **Token verification** happens in `assistant_web.py.get_current_user()` via `Authorization` header
3. **Permission checks** in update/delete operations verify user_id matches record owner
4. **Foreign key cascades** auto-delete user data when user is deleted

## API Endpoint Patterns

### Authentication
- POST `/api/auth/register` - Create user
- POST `/api/auth/login` - Get token
- POST `/api/auth/logout` - Invalidate token
- GET/POST `/api/auth/verify` - Check token validity

### Chat & AI
- POST `/api/ai/chat` - Send message, get AI response
- POST `/api/ai/clear` - Clear conversation history
- GET `/api/chats` - Get recent 100 messages
- GET `/api/chat/history` - Get last 24h messages

### Plans
- GET `/api/plans` - List user's plans
- POST `/api/plan/add` - Create plan
- POST `/api/plan/update` - Update status
- POST `/api/plan/delete` - Delete plan
- POST `/api/plan/add-detected` - Quick-save AI-detected plan

### Reminders
- GET `/api/reminders` - List user's reminders
- POST `/api/reminder/add` - Create reminder
- POST `/api/reminder/delete` - Delete reminder

### Images
- GET `/api/images` - List user's images
- POST `/api/image/upload` - Upload file (multipart/form-data)
- GET `/uploads/images/<filename>` - Serve image file
- GET `/uploads/avatars/<filename>` - Serve avatar file

### User Profile
- GET `/api/user/profile` - Get current user info
- POST `/api/user/change-password` - Change password
- POST `/api/user/upload-avatar` - Update avatar

All except auth endpoints require `Authorization: Bearer <token>` header.

## File Locations on Production Server

```
/var/www/ai-assistant/
├── assistant_web.py         # Main server
├── ai_chat_assistant.py
├── mysql_manager.py
├── user_manager.py
├── reminder_scheduler.py
├── notification_service.py
├── mysql_config.json         # Git-ignored
├── ai_config.json            # Git-ignored
├── uploads/
│   ├── avatars/
│   └── images/
└── deploy/
    ├── DEPLOYMENT_GUIDE.md
    └── DATABASE_SETUP.md

/etc/nginx/sites-available/default
  └── location /ai/ { proxy_pass http://127.0.0.1:8000/; }

/etc/supervisor/conf.d/ai-assistant.conf
  └── Manages assistant_web.py process

/var/log/
├── ai-assistant.log          # Application stdout
└── ai-assistant-error.log    # Application stderr
```

## Testing API Locally

```bash
# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123","phone":""}'

# Login and get token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}' | jq -r '.token')

# Send chat message
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"明天完成报表"}'

# List plans
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plans
```

## Important Code Locations

### Where user authentication happens
- `assistant_web.py:33-49` - `get_current_user()` and `require_auth()`

### Where relative time is parsed
- `ai_chat_assistant.py:169-244` - Main parser with all time patterns
- `assistant_web.py:51-120` - Duplicated in web handler

### Where shortcuts are processed
- `ai_chat_assistant.py:386-667` - `process_shortcut_command()`

### Where AI context is built
- `ai_chat_assistant.py:59-132` - `get_smart_context()` - keyword search + recent data

### Where plans are auto-detected
- `ai_chat_assistant.py:814-882` - `extract_plans_from_message()`

### Where completion is detected
- `ai_chat_assistant.py:964-1060` - `detect_and_complete_plans()`

### Database manager initialization
- `mysql_manager.py:16-83` - `MySQLManager` class with connection handling
- `mysql_manager.py:120-321` - `MemoryManagerMySQL` for messages
- `mysql_manager.py:766-905` - `WorkPlanManagerMySQL` for plans

## Special Notes for AI Development

When modifying chat/AI features:
1. Context window is limited by `max_tokens: 300` - keep context concise
2. Smart context only includes recent 15 chats + 10 plans to save tokens
3. Keyword matching is case-sensitive and uses LIKE %keyword%
4. User's conversation history is stored per-user in `AIAssistant.conversation_history` dict
5. Clearing conversation (`clear_conversation`) only clears in-memory history, not database

When modifying time-related features:
1. All three parsers should be kept in sync (ai_chat_assistant, assistant_web, reminder_scheduler)
2. "明早" logic depends on current_hour - test edge cases around 6:00 AM
3. Time phrases like "下午", "晚上" with no explicit date default to TODAY

When modifying multi-user features:
1. ALWAYS pass user_id parameter to all data access methods
2. Test with multiple users to verify data isolation
3. Foreign key constraints will CASCADE DELETE - be careful with user deletion
4. Sessions auto-expire after 7 days - implement refresh token if needed
