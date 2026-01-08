#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQLite数据库管理类
从mysql_manager.py转换而来，使用SQLite替代MySQL
提供数据库连接、查询、事务管理等功能
"""

import sqlite3
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
import os


class SQLiteManager:
    """SQLite数据库管理器（替代MySQLManager）"""

    def __init__(self, db_path=None):
        """初始化SQLite连接

        Args:
            db_path: 数据库文件路径，默认使用 ~/Library/Application Support/AIAssistant/data.db
        """
        if db_path is None:
            # Mac Application Support目录
            data_dir = os.path.expanduser('~/Library/Application Support/AIAssistant')
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, 'data.db')

        self.db_path = os.path.abspath(db_path)
        self.connection = None
        self._connect()
        self._initialize_database()

    def _connect(self):
        """建立数据库连接"""
        try:
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,  # 允许多线程访问
                timeout=30.0  # 30秒超时
            )
            # 使用Row工厂，返回类似字典的对象
            self.connection.row_factory = sqlite3.Row
            # 启用外键约束
            self.connection.execute("PRAGMA foreign_keys = ON")
            # WAL模式提升并发性能
            self.connection.execute("PRAGMA journal_mode = WAL")
            print(f"✅ SQLite connected: {self.db_path}")
        except Exception as e:
            print(f"❌ SQLite connection failed: {e}")
            raise

    def _initialize_database(self):
        """初始化数据库（如果是新数据库，执行schema）"""
        # 检查是否已有表
        cursor = self.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            # 数据库为空，执行schema
            schema_path = os.path.join(os.path.dirname(__file__), 'config', 'db_schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                # SQLite允许一次执行多条SQL
                self.connection.executescript(schema_sql)
                print(f"✅ Database initialized from schema")
        cursor.close()

    def ensure_connection(self):
        """确保数据库连接有效"""
        try:
            if self.connection is None:
                self._connect()
            else:
                # 尝试执行简单查询验证连接
                self.connection.execute("SELECT 1")
        except Exception as e:
            print(f"⚠️ Reconnecting to SQLite: {e}")
            self._connect()

    @contextmanager
    def get_cursor(self):
        """获取数据库游标（上下文管理器）"""
        self.ensure_connection()
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()  # 提交事务
        except Exception as e:
            self.connection.rollback()  # 事务失败时回滚
            raise
        finally:
            cursor.close()

    def execute(self, sql, params=None):
        """执行SQL语句（INSERT/UPDATE/DELETE）

        注意：SQLite使用 ? 作为占位符，不是 %s
        """
        # 调试日志
        if 'work_plans' in sql and 'INSERT' in sql:
            print(f"🔍 执行SQL: {sql[:80]}...")
            print(f"🔍 参数: {params}")

        with self.get_cursor() as cursor:
            try:
                cursor.execute(sql, params or ())
                return cursor.lastrowid
            except Exception as e:
                print(f"❌ SQL执行失败: {e}")
                print(f"❌ SQL: {sql}")
                print(f"❌ Params: {params}")
                raise

    def query(self, sql, params=None):
        """执行查询语句（SELECT）

        返回：Row对象列表（可以像字典一样访问）
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()
            # 转换Row对象为字典
            return [dict(row) for row in rows]

    def query_one(self, sql, params=None):
        """执行查询并返回单条记录"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            row = cursor.fetchone()
            return dict(row) if row else None

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("SQLite connection closed")


class MemoryManagerSQLite:
    """基于SQLite的对话记忆管理器"""

    def __init__(self, db_manager):
        self.db = db_manager

    def add_message(self, role, content, tags=None, image_url=None, user_id=None, file_id=None):
        """添加消息到数据库"""
        sql = """
            INSERT INTO messages (user_id, role, content, tags, image_url, file_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tags_json = json.dumps(tags or [], ensure_ascii=False) if tags else None

        message_id = self.db.execute(sql, (user_id, role, content, tags_json, image_url, file_id, timestamp))
        return message_id

    def get_recent_messages(self, limit=10, user_id=None):
        """获取最近的消息"""
        # ✅ 安全检查：确保user_id存在，防止返回所有用户数据
        if user_id is None:
            return []  # 未授权用户无法查询任何数据

        sql = """
            SELECT m.id, m.role, m.content, m.timestamp, m.tags, m.image_url,
                   f.id as file_id, f.original_name as file_name, f.file_size, f.mime_type, f.file_path, f.filename
            FROM messages m
            LEFT JOIN files f ON m.file_id = f.id
            WHERE m.user_id = ?
            ORDER BY m.timestamp DESC
            LIMIT ?
        """
        messages = self.db.query(sql, (user_id, limit))

        # 解析JSON字段和转换日期
        for msg in messages:
            if msg['tags']:
                try:
                    msg['tags'] = json.loads(msg['tags'])
                except:
                    msg['tags'] = []
            else:
                msg['tags'] = []

            # 构造 file_info
            if msg.get('file_id'):
                msg['file_info'] = {
                    'id': msg['file_id'],
                    'name': msg['file_name'],
                    'filename': msg['filename'],
                    'size': msg['file_size'],
                    'type': msg['mime_type'],
                    'path': msg['file_path']
                }

            # SQLite返回的timestamp已是字符串，无需转换
            # 如果是datetime对象则转换
            if msg['timestamp'] and isinstance(msg['timestamp'], datetime):
                msg['timestamp'] = msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

        return list(reversed(messages))  # 返回正序

    def get_messages_last_24h(self, user_id):
        """获取最近24小时的消息"""
        if user_id is None:
            return []

        # 计算24小时前的时间
        start_time = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')

        sql = """
            SELECT m.id, m.role, m.content, m.timestamp, m.tags, m.image_url,
                   f.id as file_id, f.original_name as file_name, f.file_size, f.mime_type, f.file_path, f.filename
            FROM messages m
            LEFT JOIN files f ON m.file_id = f.id
            WHERE m.user_id = ? AND m.timestamp >= ?
            ORDER BY m.timestamp ASC
        """
        messages = self.db.query(sql, (user_id, start_time))

        # 解析JSON字段
        for msg in messages:
            if msg['tags']:
                try:
                    msg['tags'] = json.loads(msg['tags'])
                except:
                    msg['tags'] = []
            else:
                msg['tags'] = []

            # 构造file_info
            if msg.get('file_id'):
                msg['file_info'] = {
                    'id': msg['file_id'],
                    'name': msg['file_name'],
                    'filename': msg['filename'],
                    'size': msg['file_size'],
                    'type': msg['mime_type'],
                    'path': msg['file_path']
                }

            # 转换datetime为字符串
            if msg['timestamp'] and isinstance(msg['timestamp'], datetime):
                msg['timestamp'] = msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

        return messages

    def delete_related_messages(self, plan_content, user_id):
        """删除与特定计划相关的消息"""
        if user_id is None:
            return 0

        sql = """
            DELETE FROM messages
            WHERE user_id = ? AND content LIKE ?
        """
        # SQLite的LIKE模式
        pattern = f'%{plan_content}%'
        return self.db.execute(sql, (user_id, pattern))

    def clear_conversation(self, user_id):
        """清空用户的对话历史"""
        if user_id is None:
            return 0

        sql = "DELETE FROM messages WHERE user_id = ?"
        return self.db.execute(sql, (user_id,))


class ReminderSystemSQLite:
    """基于SQLite的提醒系统"""

    def __init__(self, db_manager):
        self.db = db_manager

    def create_reminder(self, content, remind_time, user_id=None):
        """创建提醒"""
        sql = """
            INSERT INTO reminders (user_id, content, remind_time, status, triggered)
            VALUES (?, ?, ?, 'pending', 0)
        """

        # 确保remind_time是字符串格式
        if isinstance(remind_time, datetime):
            remind_time = remind_time.strftime('%Y-%m-%d %H:%M:%S')

        reminder_id = self.db.execute(sql, (user_id, content, remind_time))
        return reminder_id

    def get_pending_reminders(self, user_id=None):
        """获取待处理的提醒"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if user_id is None:
            # 获取所有用户的提醒（用于后台任务）
            sql = """
                SELECT id, user_id, content, remind_time, status, triggered
                FROM reminders
                WHERE status = 'pending' AND remind_time <= ? AND triggered = 0
                ORDER BY remind_time ASC
            """
            return self.db.query(sql, (now,))
        else:
            # 获取特定用户的提醒
            sql = """
                SELECT id, user_id, content, remind_time, status, triggered
                FROM reminders
                WHERE user_id = ? AND status = 'pending' AND remind_time <= ? AND triggered = 0
                ORDER BY remind_time ASC
            """
            return self.db.query(sql, (user_id, now))

    def mark_triggered(self, reminder_id):
        """标记提醒已触发"""
        sql = """
            UPDATE reminders
            SET triggered = 1
            WHERE id = ?
        """
        return self.db.execute(sql, (reminder_id,))

    def update_status(self, reminder_id, status):
        """更新提醒状态"""
        sql = """
            UPDATE reminders
            SET status = ?
            WHERE id = ?
        """
        return self.db.execute(sql, (status, reminder_id))

    def get_user_reminders(self, user_id, status='pending'):
        """获取用户的提醒列表"""
        if user_id is None:
            return []

        if status == 'all':
            sql = """
                SELECT id, content, remind_time, status, triggered, created_at
                FROM reminders
                WHERE user_id = ?
                ORDER BY remind_time DESC
            """
            return self.db.query(sql, (user_id,))
        else:
            sql = """
                SELECT id, content, remind_time, status, triggered, created_at
                FROM reminders
                WHERE user_id = ? AND status = ?
                ORDER BY remind_time DESC
            """
            return self.db.query(sql, (user_id, status))

    def delete_reminder(self, reminder_id, user_id=None):
        """删除提醒（需要验证user_id）"""
        if user_id is None:
            return 0

        sql = """
            DELETE FROM reminders
            WHERE id = ? AND user_id = ?
        """
        return self.db.execute(sql, (reminder_id, user_id))


class ImageManagerSQLite:
    """基于SQLite的图片管理器"""

    def __init__(self, db_manager):
        self.db = db_manager

    def add_image(self, filename, original_name, file_path, description=None, tags=None, chat_id=None, file_size=None, mime_type=None, user_id=None):
        """添加图片记录"""
        sql = """
            INSERT INTO images (user_id, filename, original_name, file_path, description, tags, chat_id, file_size, mime_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        tags_json = json.dumps(tags or [], ensure_ascii=False) if tags else None

        image_id = self.db.execute(sql, (user_id, filename, original_name, file_path, description, tags_json, chat_id, file_size, mime_type))
        return image_id

    def get_user_images(self, user_id, limit=50):
        """获取用户的图片列表"""
        if user_id is None:
            return []

        sql = """
            SELECT id, filename, original_name, file_path, description, tags, chat_id, file_size, mime_type, created_at
            FROM images
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        images = self.db.query(sql, (user_id, limit))

        # 解析JSON tags
        for img in images:
            if img['tags']:
                try:
                    img['tags'] = json.loads(img['tags'])
                except:
                    img['tags'] = []
            else:
                img['tags'] = []

        return images

    def delete_image(self, image_id, user_id=None):
        """删除图片记录（需要验证user_id）"""
        if user_id is None:
            return 0

        # 先获取文件路径以便删除物理文件
        sql_select = "SELECT file_path FROM images WHERE id = ? AND user_id = ?"
        image = self.db.query_one(sql_select, (image_id, user_id))

        if image:
            # 删除数据库记录
            sql_delete = "DELETE FROM images WHERE id = ? AND user_id = ?"
            self.db.execute(sql_delete, (image_id, user_id))
            return image['file_path']

        return None


class WorkPlanManagerSQLite:
    """基于SQLite的工作计划管理器"""

    def __init__(self, db_manager):
        self.db = db_manager

    def create_plan(self, title, content, priority='medium', due_date=None, tags=None, user_id=None):
        """创建工作计划"""
        sql = """
            INSERT INTO work_plans (user_id, title, content, priority, status, due_date, tags)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """
        tags_json = json.dumps(tags or [], ensure_ascii=False) if tags else None

        # 确保due_date格式正确
        if isinstance(due_date, datetime):
            due_date = due_date.strftime('%Y-%m-%d %H:%M:%S')

        plan_id = self.db.execute(sql, (user_id, title, content, priority, due_date, tags_json))
        return plan_id

    def list_plans(self, user_id, status='all'):
        """获取用户的计划列表"""
        if user_id is None:
            return []

        if status == 'all':
            sql = """
                SELECT id, title, content, priority, status, due_date, tags, created_at, updated_at, completed_at
                FROM work_plans
                WHERE user_id = ?
                ORDER BY
                    CASE priority
                        WHEN 'urgent' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                    END,
                    due_date ASC NULLS LAST,
                    created_at DESC
            """
            plans = self.db.query(sql, (user_id,))
        else:
            sql = """
                SELECT id, title, content, priority, status, due_date, tags, created_at, updated_at, completed_at
                FROM work_plans
                WHERE user_id = ? AND status = ?
                ORDER BY
                    CASE priority
                        WHEN 'urgent' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                    END,
                    due_date ASC NULLS LAST,
                    created_at DESC
            """
            plans = self.db.query(sql, (user_id, status))

        # 解析JSON tags
        for plan in plans:
            if plan['tags']:
                try:
                    plan['tags'] = json.loads(plan['tags'])
                except:
                    plan['tags'] = []
            else:
                plan['tags'] = []

        return plans

    def update_plan_status(self, plan_id, status, user_id=None):
        """更新计划状态"""
        if user_id is None:
            return 0

        # 如果是完成状态，记录完成时间
        if status == 'completed':
            sql = """
                UPDATE work_plans
                SET status = ?, completed_at = datetime('now', 'localtime')
                WHERE id = ? AND user_id = ?
            """
        else:
            sql = """
                UPDATE work_plans
                SET status = ?
                WHERE id = ? AND user_id = ?
            """

        return self.db.execute(sql, (status, plan_id, user_id))

    def delete_plan(self, plan_id, user_id=None):
        """删除计划"""
        if user_id is None:
            return 0

        sql = """
            DELETE FROM work_plans
            WHERE id = ? AND user_id = ?
        """
        return self.db.execute(sql, (plan_id, user_id))

    def search_plans(self, keyword, user_id):
        """搜索计划"""
        if user_id is None:
            return []

        sql = """
            SELECT id, title, content, priority, status, due_date, tags, created_at
            FROM work_plans
            WHERE user_id = ? AND (title LIKE ? OR content LIKE ?)
            ORDER BY created_at DESC
        """
        pattern = f'%{keyword}%'
        plans = self.db.query(sql, (user_id, pattern, pattern))

        # 解析JSON tags
        for plan in plans:
            if plan['tags']:
                try:
                    plan['tags'] = json.loads(plan['tags'])
                except:
                    plan['tags'] = []
            else:
                plan['tags'] = []

        return plans


class FileManagerSQLite:
    """基于SQLite的文件管理器"""

    def __init__(self, db_manager):
        self.db = db_manager

    def add_file(self, filename, original_name, file_path, file_size=None, mime_type=None, description=None, tags=None, user_id=None):
        """添加文件记录"""
        sql = """
            INSERT INTO files (user_id, filename, original_name, file_path, file_size, mime_type, description, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        tags_json = json.dumps(tags or [], ensure_ascii=False) if tags else None

        file_id = self.db.execute(sql, (user_id, filename, original_name, file_path, file_size, mime_type, description, tags_json))
        return file_id

    def get_user_files(self, user_id, limit=100):
        """获取用户的文件列表"""
        if user_id is None:
            return []

        sql = """
            SELECT id, filename, original_name, file_path, file_size, mime_type, description, tags, created_at
            FROM files
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        files = self.db.query(sql, (user_id, limit))

        # 解析JSON tags
        for f in files:
            if f['tags']:
                try:
                    f['tags'] = json.loads(f['tags'])
                except:
                    f['tags'] = []
            else:
                f['tags'] = []

        return files

    def delete_file(self, file_id, user_id=None):
        """删除文件记录"""
        if user_id is None:
            return 0

        # 先获取文件路径
        sql_select = "SELECT file_path FROM files WHERE id = ? AND user_id = ?"
        file = self.db.query_one(sql_select, (file_id, user_id))

        if file:
            # 删除数据库记录
            sql_delete = "DELETE FROM files WHERE id = ? AND user_id = ?"
            self.db.execute(sql_delete, (file_id, user_id))
            return file['file_path']

        return None


class KeywordManagerSQLite:
    """基于SQLite的关键词管理器"""

    def __init__(self, db_manager):
        self.db = db_manager

    def add_keyword(self, keyword, source='user', user_id=None):
        """添加关键词"""
        # 检查是否已存在
        sql_check = """
            SELECT id FROM search_keywords
            WHERE keyword = ? AND user_id IS ?
        """
        existing = self.db.query_one(sql_check, (keyword, user_id))

        if existing:
            return existing['id']

        sql = """
            INSERT INTO search_keywords (keyword, source, user_id)
            VALUES (?, ?, ?)
        """
        return self.db.execute(sql, (keyword, source, user_id))

    def get_keywords(self, user_id=None, source='all'):
        """获取关键词列表"""
        if source == 'all':
            if user_id is None:
                # 获取系统级别关键词
                sql = """
                    SELECT DISTINCT keyword FROM search_keywords
                    WHERE user_id IS NULL OR source = 'system'
                    ORDER BY created_at DESC
                """
                keywords = self.db.query(sql)
            else:
                # 获取系统 + 用户级别
                sql = """
                    SELECT DISTINCT keyword FROM search_keywords
                    WHERE user_id IS NULL OR user_id = ? OR source IN ('system', 'global')
                    ORDER BY created_at DESC
                """
                keywords = self.db.query(sql, (user_id,))
        else:
            sql = """
                SELECT DISTINCT keyword FROM search_keywords
                WHERE source = ? AND (user_id IS NULL OR user_id = ?)
                ORDER BY created_at DESC
            """
            keywords = self.db.query(sql, (source, user_id))

        return [k['keyword'] for k in keywords]

    def delete_keyword(self, keyword, user_id=None):
        """删除关键词"""
        if user_id is None:
            # 只能删除系统关键词
            sql = """
                DELETE FROM search_keywords
                WHERE keyword = ? AND user_id IS NULL
            """
            return self.db.execute(sql, (keyword,))
        else:
            # 删除用户自己的关键词
            sql = """
                DELETE FROM search_keywords
                WHERE keyword = ? AND user_id = ?
            """
            return self.db.execute(sql, (keyword, user_id))
