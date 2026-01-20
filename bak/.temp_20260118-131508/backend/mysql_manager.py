#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MySQL数据库管理类
提供数据库连接、查询、事务管理等功能
"""

import pymysql
from pymysql.cursors import DictCursor
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
import os

class MySQLManager:
    """MySQL数据库管理器"""
    
    def __init__(self, config_file='mysql_config.json'):
        """初始化MySQL连接"""
        self.config = self._load_config(config_file)
        self.connection = None
        self._connect()
    
    def _load_config(self, config_file):
        """加载MySQL配置"""
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"MySQL config file not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 验证必需配置项
        required_keys = ['host', 'user', 'password', 'database']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")
        
        return config
    
    def _connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.config['host'],
                port=self.config.get('port', 3306),
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset=self.config.get('charset', 'utf8mb4'),
                cursorclass=DictCursor,
                autocommit=self.config.get('autocommit', True)
            )
            print(f"✅ MySQL connected: {self.config['database']}")
        except Exception as e:
            print(f"❌ MySQL connection failed: {e}")
            raise
    
    def ensure_connection(self):
        """确保数据库连接有效"""
        try:
            if self.connection is None or not self.connection.open:
                self._connect()
            else:
                self.connection.ping(reconnect=True)
        except Exception as e:
            print(f"⚠️ Reconnecting to MySQL: {e}")
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
        """执行SQL语句（INSERT/UPDATE/DELETE）"""
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
        """执行查询语句（SELECT）"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
    
    def query_one(self, sql, params=None):
        """执行查询并返回单条记录"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone()
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("MySQL connection closed")


class MemoryManagerMySQL:
    """基于MySQL的对话记忆管理器"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def add_message(self, role, content, tags=None, image_url=None, user_id=None, file_id=None):
        """添加消息到数据库"""
        sql = """
            INSERT INTO messages (user_id, role, content, tags, image_url, file_id, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
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
            WHERE m.user_id = %s
            ORDER BY m.timestamp DESC
            LIMIT %s
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

            # 转换datetime为字符串
            if msg['timestamp'] and hasattr(msg['timestamp'], 'strftime'):
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
            WHERE m.user_id = %s AND m.timestamp >= %s
            ORDER BY m.timestamp ASC
        """
        messages = self.db.query(sql, (user_id, start_time))

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

            # 转换datetime为字符串
            if msg['timestamp'] and hasattr(msg['timestamp'], 'strftime'):
                msg['timestamp'] = msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

        return messages
    
    def search_messages(self, keyword=None, tags=None, limit=50, user_id=None):
        """搜索消息"""
        # ✅ 安全检查：确保user_id存在，防止返回所有用户数据
        if user_id is None:
            return []  # 未授权用户无法搜索任何数据

        conditions = ["m.user_id = %s"]  # 必须包含user_id过滤
        params = [user_id]

        if keyword:
            conditions.append("m.content LIKE %s")
            params.append(f"%{keyword}%")

        if tags:
            for tag in tags:
                conditions.append("JSON_CONTAINS(m.tags, %s)")
                params.append(json.dumps(tag, ensure_ascii=False))

        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT m.id, m.role, m.content, m.timestamp, m.tags, m.image_url,
                   f.id as file_id, f.original_name as file_name, f.file_size, f.mime_type, f.file_path
            FROM messages m
            LEFT JOIN files f ON m.file_id = f.id
            WHERE {where_clause}
            ORDER BY m.timestamp DESC
            LIMIT %s
        """
        params.append(limit)

        messages = self.db.query(sql, params)
        
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
                    'size': msg['file_size'],
                    'type': msg['mime_type'],
                    'path': msg['file_path']
                }

            # 转换datetime为字符串
            if msg['timestamp'] and hasattr(msg['timestamp'], 'strftime'):
                msg['timestamp'] = msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        return messages
    
    def get_all_messages(self, user_id=None):
        """获取所有消息"""
        if user_id is not None:
            sql = """
                SELECT m.id, m.role, m.content, m.timestamp, m.tags, m.image_url,
                       f.id as file_id, f.original_name as file_name, f.file_size, f.mime_type, f.file_path
                FROM messages m
                LEFT JOIN files f ON m.file_id = f.id
                WHERE m.user_id = %s
                ORDER BY m.timestamp ASC
            """
            messages = self.db.query(sql, (user_id,))
        else:
            sql = """
                SELECT m.id, m.role, m.content, m.timestamp, m.tags, m.image_url,
                       f.id as file_id, f.original_name as file_name, f.file_size, f.mime_type, f.file_path
                FROM messages m
                LEFT JOIN files f ON m.file_id = f.id
                ORDER BY m.timestamp ASC
            """
            messages = self.db.query(sql)
        
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
                    'size': msg['file_size'],
                    'type': msg['mime_type'],
                    'path': msg['file_path']
                }

            # 转换datetime为字符串
            if msg['timestamp'] and hasattr(msg['timestamp'], 'strftime'):
                msg['timestamp'] = msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        return messages

    def delete_messages_by_keywords(self, keywords, user_id=None):
        """删除包含特定关键词的消息（用于清理过时的聊天记录）"""
        if not keywords or user_id is None:
            return 0

        # 构建包含多个关键词的WHERE条件
        conditions = ["user_id = %s"]
        params = [user_id]

        # 任何关键词匹配都删除
        or_conditions = []
        for keyword in keywords:
            or_conditions.append("content LIKE %s")
            params.append(f"%{keyword}%")

        if or_conditions:
            conditions.append(f"({' OR '.join(or_conditions)})")

        where_clause = " AND ".join(conditions)
        sql = f"DELETE FROM messages WHERE {where_clause}"

        result = self.db.execute(sql, params)
        return result

    def clear_all(self):
        """清空所有消息"""
        sql = "DELETE FROM messages"
        self.db.execute(sql)
        return True
    
    # 兼容旧接口的方法别名
    def search_by_keyword(self, keyword, user_id=None):
        """兼容旧接口：按关键词搜索"""
        return self.search_messages(keyword=keyword, user_id=user_id)
    
    def get_recent_conversations(self, count=10, user_id=None):
        """兼容旧接口：获取最近对话"""
        return self.get_recent_messages(limit=count, user_id=user_id)
    
    @property
    def conversations(self):
        """兼容旧接口：获取所有对话（作为属性）"""
        return self.get_all_messages()


class ReminderSystemMySQL:
    """基于MySQL的提醒系统"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.running = False
        self.monitor_thread = None
    
    def add_reminder(self, title=None, message=None, remind_time=None, repeat='不重复', sound='Ping', content=None, user_id=None):
        """添加提醒（兼容新旧接口）"""
        # 兼容两种调用方式
        if content is None:
            # 旧接口：add_reminder(title, message, remind_time, ...)
            content = message or title

        if not content or not remind_time:
            raise ValueError("content和remind_time是必需的")

        sql = """
            INSERT INTO reminders (user_id, content, remind_time, status, triggered)
            VALUES (%s, %s, %s, 'pending', 0)
        """
        reminder_id = self.db.execute(sql, (user_id, content, remind_time))

        # 返回兼容格式
        return {
            'id': reminder_id,
            'message': content,
            'content': content,
            'remind_time': remind_time,
            'status': 'pending'
        }
    
    def get_pending_reminders(self, user_id=None):
        """获取所有待处理的提醒"""
        if user_id is not None:
            sql = """
                SELECT id, content, remind_time, status, triggered
                FROM reminders
                WHERE status = 'pending' AND user_id = %s
                ORDER BY remind_time ASC
            """
            return self.db.query(sql, (user_id,))
        else:
            sql = """
                SELECT id, content, remind_time, status, triggered
                FROM reminders
                WHERE status = 'pending'
                ORDER BY remind_time ASC
            """
            return self.db.query(sql)
    
    @property
    def reminders(self):
        """兼容旧接口：获取所有提醒（作为属性）"""
        sql = """
            SELECT id, content, remind_time, status, triggered, created_at
            FROM reminders
            ORDER BY remind_time ASC
        """
        results = self.db.query(sql)

        # 转换为兼容格式
        formatted = []
        for r in results:
            formatted.append({
                'id': r['id'],
                'message': r['content'],
                'content': r['content'],
                'remind_time': r['remind_time'].strftime('%Y-%m-%d %H:%M') if hasattr(r['remind_time'], 'strftime') else str(r['remind_time']),
                'status': '已触发' if r['triggered'] else ('已完成' if r['status'] == 'completed' else '活跃'),
                'created_at': r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(r['created_at'], 'strftime') else str(r['created_at'])
            })
        return formatted

    def list_reminders(self, user_id=None):
        """获取提醒列表（兼容旧接口）"""
        sql = """
            SELECT id, content, remind_time, status, triggered, created_at
            FROM reminders
            WHERE user_id = %s
            ORDER BY remind_time ASC
        """
        results = self.db.query(sql, (user_id,)) if user_id else []

        # 转换为兼容格式
        formatted = []
        for r in results:
            formatted.append({
                'id': r['id'],
                'message': r['content'],
                'content': r['content'],
                'remind_time': r['remind_time'].strftime('%Y-%m-%d %H:%M') if hasattr(r['remind_time'], 'strftime') else str(r['remind_time']),
                'status': '已触发' if r['triggered'] else ('已完成' if r['status'] == 'completed' else '活跃'),
                'created_at': r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(r['created_at'], 'strftime') else str(r['created_at'])
            })
        return formatted
    
    def get_due_reminders(self):
        """获取到期且未触发的提醒"""
        sql = """
            SELECT id, content, remind_time
            FROM reminders
            WHERE status = 'pending' 
                AND triggered = 0
                AND remind_time <= NOW()
            ORDER BY remind_time ASC
        """
        return self.db.query(sql)
    
    def mark_triggered(self, reminder_id):
        """标记提醒已触发"""
        sql = """
            UPDATE reminders
            SET triggered = 1
            WHERE id = %s
        """
        self.db.execute(sql, (reminder_id,))
    
    def complete_reminder(self, reminder_id):
        """完成提醒"""
        sql = """
            UPDATE reminders
            SET status = 'completed'
            WHERE id = %s
        """
        self.db.execute(sql, (reminder_id,))
    
    def delete_reminder(self, reminder_id, user_id=None):
        """删除提醒"""
        if user_id is not None:
            # 先检查权限
            check_sql = "SELECT user_id FROM reminders WHERE id = %s"
            result = self.db.query_one(check_sql, (reminder_id,))
            if result and result.get('user_id') != user_id:
                return False  # 权限不足

        sql = "DELETE FROM reminders WHERE id = %s"
        self.db.execute(sql, (reminder_id,))
        return True
    
    def start_monitoring(self):
        """启动提醒监控线程"""
        if not self.running:
            import threading
            import time
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            print("✅ 提醒监控已启动（MySQL）")
    
    def stop_monitoring(self):
        """停止提醒监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("⏹️ 提醒监控已停止")
    
    def _monitor_loop(self):
        """监控循环，每10秒检查一次"""
        import time
        while self.running:
            try:
                self.check_reminders()
            except Exception as e:
                print(f"提醒检查出错: {e}")
            time.sleep(10)  # 每10秒检查一次
    
    def check_reminders(self):
        """检查是否有到期的提醒"""
        due_reminders = self.get_due_reminders()
        
        for reminder in due_reminders:
            try:
                self.trigger_reminder(reminder)
            except Exception as e:
                print(f"处理提醒时出错: {e}")
    
    def trigger_reminder(self, reminder):
        """触发提醒通知"""
        import subprocess
        
        print(f"\n🔔 提醒触发: {reminder['content']}")
        
        # 1. 显示系统通知
        self.show_notification("提醒", reminder['content'])
        
        # 2. 播放声音
        self.play_sound()
        
        # 3. 更新提醒状态
        self.mark_triggered(reminder['id'])
        
        print(f"✅ 提醒已触发")
    
    def show_notification(self, title, message):
        """显示macOS系统通知"""
        import subprocess
        try:
            script = f'''
            display notification "{message}" with title "⏰ {title}" sound name "Glass"
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True)
        except Exception as e:
            print(f"显示通知失败: {e}")
    
    def play_sound(self):
        """播放提醒声音"""
        import subprocess
        try:
            # 使用系统声音
            subprocess.run(['afplay', '/System/Library/Sounds/Ping.aiff'], 
                          check=False, capture_output=True)
            # 再播放一次产生"叮叮"效果
            import time
            time.sleep(0.3)
            subprocess.run(['afplay', '/System/Library/Sounds/Ping.aiff'], 
                          check=False, capture_output=True)
        except Exception as e:
            print(f"播放声音失败: {e}")


class ImageManagerMySQL:
    """基于MySQL的图片管理器"""
    
    def __init__(self, db_manager, upload_dir='uploads/images'):
        self.db = db_manager
        self.upload_dir = upload_dir
        
        # 创建上传目录
        import os
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
    
    def add_image(self, filename, original_name, file_path, description=None,
                  tags=None, chat_id=None, file_size=None, mime_type=None, user_id=None):
        """添加图片记录"""
        sql = """
            INSERT INTO images
            (user_id, filename, original_name, file_path, description, tags, chat_id, file_size, mime_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        tags_json = json.dumps(tags or [], ensure_ascii=False) if tags else None

        image_id = self.db.execute(sql, (
            user_id, filename, original_name, file_path, description,
            tags_json, chat_id, file_size, mime_type
        ))
        return image_id
    
    def search_images(self, keyword=None, tags=None, tag=None, chat_id=None, user_id=None):
        """搜索图片（兼容旧接口）"""
        conditions = []
        params = []

        if user_id is not None:
            conditions.append("user_id = %s")
            params.append(user_id)

        if keyword:
            conditions.append("(description LIKE %s OR original_name LIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        # 兼容 tag 和 tags 参数
        if tag:
            conditions.append("JSON_CONTAINS(tags, %s)")
            params.append(json.dumps(tag, ensure_ascii=False))

        if tags:
            for t in tags:
                conditions.append("JSON_CONTAINS(tags, %s)")
                params.append(json.dumps(t, ensure_ascii=False))

        if chat_id:
            conditions.append("chat_id = %s")
            params.append(chat_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT id, filename, original_name, file_path, description, tags,
                   chat_id, file_size, mime_type, created_at
            FROM images
            WHERE {where_clause}
            ORDER BY created_at DESC
        """

        images = self.db.query(sql, params)

        # 解析JSON字段和转换日期
        for img in images:
            if img['tags']:
                try:
                    img['tags'] = json.loads(img['tags'])
                except:
                    img['tags'] = []
            else:
                img['tags'] = []

            # 转换datetime为字符串
            if img.get('created_at') and hasattr(img['created_at'], 'strftime'):
                img['created_at'] = img['created_at'].strftime('%Y-%m-%d %H:%M:%S')

            # 确保 file_path 格式正确（以/开头，用于前端）
            if img['file_path'] and not img['file_path'].startswith('/'):
                img['file_path'] = f"/{img['file_path']}"

        return images
    
    def get_all_images(self, user_id=None):
        """获取所有图片"""
        if user_id is not None:
            sql = """
                SELECT id, filename, original_name, file_path, description, tags,
                       chat_id, file_size, mime_type, created_at
                FROM images
                WHERE user_id = %s
                ORDER BY created_at DESC
            """
            images = self.db.query(sql, (user_id,))
        else:
            sql = """
                SELECT id, filename, original_name, file_path, description, tags,
                       chat_id, file_size, mime_type, created_at
                FROM images
                ORDER BY created_at DESC
            """
            images = self.db.query(sql)

        # 解析JSON字段和转换日期
        for img in images:
            if img['tags']:
                try:
                    img['tags'] = json.loads(img['tags'])
                except:
                    img['tags'] = []
            else:
                img['tags'] = []

            # 转换datetime为字符串
            if img.get('created_at') and hasattr(img['created_at'], 'strftime'):
                img['created_at'] = img['created_at'].strftime('%Y-%m-%d %H:%M:%S')

            # 确保 file_path 格式正确（以/开头，用于前端）
            if img['file_path'] and not img['file_path'].startswith('/'):
                img['file_path'] = f"/{img['file_path']}"

        return images
    
    def delete_image(self, image_id, user_id=None):
        """删除图片记录"""
        if user_id is not None:
            # 先检查权限
            check_sql = "SELECT user_id FROM images WHERE id = %s"
            result = self.db.query_one(check_sql, (image_id,))
            if result and result.get('user_id') != user_id:
                return False  # 权限不足

        sql = "DELETE FROM images WHERE id = %s"
        self.db.execute(sql, (image_id,))
        return True
    
    def update_image(self, image_id, description=None, tags=None, user_id=None):
        """更新图片信息"""
        # 如果指定了user_id，先检查权限
        if user_id is not None:
            check_sql = "SELECT user_id FROM images WHERE id = %s"
            result = self.db.query_one(check_sql, (image_id,))
            if result and result.get('user_id') != user_id:
                return False  # 权限不足

        if description is not None:
            sql = "UPDATE images SET description = %s WHERE id = %s"
            self.db.execute(sql, (description, image_id))

        if tags is not None:
            tags_json = json.dumps(tags, ensure_ascii=False)
            sql = "UPDATE images SET tags = %s WHERE id = %s"
            self.db.execute(sql, (tags_json, image_id))

        return True
    
    def get_image_by_id(self, image_id):
        """根据ID获取图片"""
        sql = """
            SELECT id, filename, original_name, file_path, description, tags,
                   chat_id, file_size, mime_type, created_at
            FROM images
            WHERE id = %s
        """
        images = self.db.query(sql, (image_id,))
        
        if images:
            img = images[0]
            if img['tags']:
                try:
                    img['tags'] = json.loads(img['tags'])
                except:
                    img['tags'] = []
            else:
                img['tags'] = []
            
            # 转换datetime为字符串
            if img.get('created_at') and hasattr(img['created_at'], 'strftime'):
                img['created_at'] = img['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            return img
        return None
    
    def list_images(self, limit=None, user_id=None):
        """列出所有图片"""
        if user_id is not None:
            sql = """
                SELECT id, filename, original_name, file_path, description, tags,
                       chat_id, file_size, mime_type, created_at
                FROM images
                WHERE user_id = %s
                ORDER BY created_at DESC
            """
            if limit:
                sql += f" LIMIT {limit}"
            images = self.db.query(sql, (user_id,))
        else:
            sql = """
                SELECT id, filename, original_name, file_path, description, tags,
                       chat_id, file_size, mime_type, created_at
                FROM images
                ORDER BY created_at DESC
            """
            if limit:
                sql += f" LIMIT {limit}"
            images = self.db.query(sql)

        # 解析JSON字段和转换日期
        for img in images:
            if img['tags']:
                try:
                    img['tags'] = json.loads(img['tags'])
                except:
                    img['tags'] = []
            else:
                img['tags'] = []

            # 转换datetime为字符串
            if img.get('created_at') and hasattr(img['created_at'], 'strftime'):
                img['created_at'] = img['created_at'].strftime('%Y-%m-%d %H:%M:%S')

            # 确保 file_path 格式正确（以/开头，用于前端）
            if img['file_path'] and not img['file_path'].startswith('/'):
                img['file_path'] = f"/{img['file_path']}"

        return images


class WorkPlanManagerMySQL:
    """MySQL工作计划管理器"""
    
    def __init__(self, db_manager=None):
        self.db = db_manager if db_manager else MySQLManager()
        print("✅ 使用MySQL工作计划管理器")
    
    def add_plan(self, title, description='', deadline=None, priority='medium', status='pending', user_id=None):
        """添加工作计划"""
        # 处理空的deadline - 如果为None或空字符串，使用当前日期
        if deadline is None or deadline == '' or deadline == 'None':
            deadline = datetime.now().strftime('%Y-%m-%d')
            print(f"📅 使用默认截止日期: {deadline}")

        print(f"📋 添加计划 - 标题: {title}, 截止日期: {deadline}, 优先级: {priority}")

        sql = """
            INSERT INTO work_tasks (user_id, title, content, due_date, priority, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            self.db.execute(sql, (user_id, title, description, deadline, priority, status))
            print(f"✅ 工作计划已添加: {title}")
        except Exception as e:
            print(f"❌ 添加计划失败: {e}")
            raise
    
    def list_plans(self, status=None, user_id=None):
        """列出工作计划"""
        conditions = []
        params = []

        if user_id is not None:
            conditions.append("user_id = %s")
            params.append(user_id)

        if status:
            conditions.append("status = %s")
            params.append(status)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT id, title, content as description, due_date as deadline, priority, status, created_at, updated_at
            FROM work_tasks
            WHERE {where_clause}
            ORDER BY created_at DESC
        """
        plans = self.db.query(sql, params if params else None)

        # 转换datetime为字符串
        for plan in plans:
            if plan.get('deadline') and hasattr(plan['deadline'], 'strftime'):
                plan['deadline'] = plan['deadline'].strftime('%Y-%m-%d %H:%M:%S')
            if plan.get('created_at') and hasattr(plan['created_at'], 'strftime'):
                plan['created_at'] = plan['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if plan.get('updated_at') and hasattr(plan['updated_at'], 'strftime'):
                plan['updated_at'] = plan['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            # ✨ 添加 source 字段，标识数据来源
            plan['source'] = 'work_tasks'

        return plans
    
    def get_plan(self, plan_id, user_id=None):
        """获取单个工作计划"""
        if user_id is not None:
            # 需要权限检查
            sql = """
                SELECT id, title, content as description, due_date as deadline, priority, status, created_at
                FROM work_tasks
                WHERE id = %s AND user_id = %s
            """
            plans = self.db.query(sql, (plan_id, user_id))
        else:
            sql = """
                SELECT id, title, content as description, due_date as deadline, priority, status, created_at
                FROM work_tasks
                WHERE id = %s
            """
            plans = self.db.query(sql, (plan_id,))

        if plans:
            plan = plans[0]
            if plan.get('deadline') and hasattr(plan['deadline'], 'strftime'):
                plan['deadline'] = plan['deadline'].strftime('%Y-%m-%d %H:%M:%S')
            if plan.get('created_at') and hasattr(plan['created_at'], 'strftime'):
                plan['created_at'] = plan['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            return plan
        return None
    
    def update_plan(self, plan_id, user_id=None, **kwargs):
        """更新工作计划"""
        # 如果指定了user_id，先检查权限
        if user_id is not None:
            check_sql = "SELECT user_id FROM work_tasks WHERE id = %s"
            result = self.db.query_one(check_sql, (plan_id,))
            if result and result.get('user_id') != user_id:
                return False  # 权限不足

        # 字段映射：前端使用的名称 -> 数据库字段名
        field_mapping = {
            'title': 'title',
            'description': 'content',
            'deadline': 'due_date',
            'priority': 'priority',
            'status': 'status'
        }
        updates = []
        values = []

        for field, value in kwargs.items():
            if field in field_mapping:
                db_field = field_mapping[field]
                updates.append(f"{db_field} = %s")
                values.append(value)

        if not updates:
            return False

        values.append(plan_id)
        sql = f"UPDATE work_tasks SET {', '.join(updates)} WHERE id = %s"
        self.db.execute(sql, tuple(values))
        print(f"✅ 工作计划已更新: ID={plan_id}")
        return True
    
    def delete_plan(self, plan_id, user_id=None):
        """删除工作计划"""
        # 如果指定了user_id，先检查权限
        if user_id is not None:
            check_sql = "SELECT user_id FROM work_tasks WHERE id = %s"
            result = self.db.query_one(check_sql, (plan_id,))
            if result and result.get('user_id') != user_id:
                return False  # 权限不足

        sql = "DELETE FROM work_tasks WHERE id = %s"
        self.db.execute(sql, (plan_id,))
        print(f"✅ 工作计划已删除: ID={plan_id}")
        return True
    
    @property
    def plans(self):
        """兼容性属性，返回所有计划列表"""
        return self.list_plans()


class FileManagerMySQL:
    """基于MySQL的通用文件管理器（支持1GB以内文件）"""

    # 文件大小限制（1GB = 1073741824字节）
    MAX_FILE_SIZE = 1073741824

    # MIME类型到分类的映射
    MIME_TO_CATEGORY = {
        'application/pdf': 'document',
        'application/msword': 'document',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'document',
        'application/vnd.ms-excel': 'document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'document',
        'application/vnd.ms-powerpoint': 'document',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'document',
        'text/plain': 'document',
        'text/csv': 'document',
        'image/jpeg': 'image',
        'image/png': 'image',
        'image/gif': 'image',
        'image/bmp': 'image',
        'image/webp': 'image',
        'video/mp4': 'video',
        'video/mpeg': 'video',
        'video/quicktime': 'video',
        'video/x-msvideo': 'video',
        'audio/mpeg': 'audio',
        'audio/wav': 'audio',
        'audio/ogg': 'audio',
        'audio/mp4': 'audio',
        'application/zip': 'archive',
        'application/x-rar-compressed': 'archive',
        'application/x-7z-compressed': 'archive',
        'application/x-tar': 'archive',
        'application/gzip': 'archive',
    }

    def __init__(self, db_manager, upload_dir='uploads/files'):
        self.db = db_manager
        self.upload_dir = upload_dir

        # 创建上传目录
        import os
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
            print(f"✅ 创建文件上传目录: {upload_dir}")

    def _get_category_from_mime(self, mime_type):
        """根据MIME类型自动识别文件分类"""
        if not mime_type or mime_type.strip() == '':
            return 'other'

        mime_type = mime_type.strip().lower()

        # 1. 尝试精确匹配
        if mime_type in self.MIME_TO_CATEGORY:
            return self.MIME_TO_CATEGORY[mime_type]

        # 2. 尝试前缀匹配（处理未在映射表中的MIME类型）
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type.startswith('text/') or 'document' in mime_type or 'word' in mime_type or 'excel' in mime_type or 'powerpoint' in mime_type or 'sheet' in mime_type or 'presentation' in mime_type:
            return 'document'
        elif 'zip' in mime_type or 'rar' in mime_type or 'tar' in mime_type or 'gzip' in mime_type or '7z' in mime_type or 'compress' in mime_type:
            return 'archive'

        # 3. 默认返回other
        return 'other'

    def _get_mime_from_extension(self, filename):
        """根据文件扩展名推断MIME类型"""
        import os
        ext = os.path.splitext(filename)[1].lower()

        mime_map = {
            # 图片
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
            '.gif': 'image/gif', '.bmp': 'image/bmp', '.webp': 'image/webp',
            '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
            # 视频
            '.mp4': 'video/mp4', '.mov': 'video/quicktime', '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska', '.webm': 'video/webm', '.flv': 'video/x-flv',
            '.wmv': 'video/x-ms-wmv', '.m4v': 'video/x-m4v',
            # 音频
            '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4', '.flac': 'audio/flac', '.aac': 'audio/aac',
            # 文档
            '.pdf': 'application/pdf', '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain', '.csv': 'text/csv',
            # 压缩包
            '.zip': 'application/zip', '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed', '.tar': 'application/x-tar',
            '.gz': 'application/gzip',
        }

        return mime_map.get(ext, 'application/octet-stream')

    def add_file(self, filename, original_name, file_path, file_size, mime_type=None,
                 description=None, tags=None, category=None, thumbnail_path=None, user_id=None):
        """添加文件记录"""
        # 检查文件大小
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"文件大小超过限制（最大1GB），当前大小: {file_size / (1024*1024):.2f}MB")

        # 如果mime_type为空或为通用类型，根据文件扩展名推断
        if not mime_type or mime_type == 'application/octet-stream':
            mime_type = self._get_mime_from_extension(original_name)

        # 自动识别分类
        if category is None and mime_type:
            category = self._get_category_from_mime(mime_type)

        sql = """
            INSERT INTO files
            (user_id, filename, original_name, file_path, file_size, mime_type,
             description, tags, category, thumbnail_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        tags_json = json.dumps(tags or [], ensure_ascii=False) if tags else None

        file_id = self.db.execute(sql, (
            user_id, filename, original_name, file_path, file_size, mime_type,
            description, tags_json, category or 'other', thumbnail_path
        ))
        print(f"✅ 文件已添加到数据库: {original_name} (ID={file_id}, 大小={file_size / (1024*1024):.2f}MB)")
        return file_id

    def search_files(self, keyword=None, category=None, tags=None, user_id=None, limit=None):
        """搜索文件"""
        conditions = []
        params = []

        if user_id is not None:
            conditions.append("user_id = %s")
            params.append(user_id)

        if keyword:
            conditions.append("(description LIKE %s OR original_name LIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        if category:
            conditions.append("category = %s")
            params.append(category)

        if tags:
            for tag in tags:
                conditions.append("JSON_CONTAINS(tags, %s)")
                params.append(json.dumps(tag, ensure_ascii=False))

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT id, filename, original_name, file_path, file_size, mime_type,
                   description, tags, category, download_count, thumbnail_path, created_at, updated_at
            FROM files
            WHERE {where_clause}
            ORDER BY created_at DESC
        """
        if limit:
            sql += f" LIMIT {limit}"

        files = self.db.query(sql, params if params else None)

        # 解析JSON字段和转换日期
        for file in files:
            if file['tags']:
                try:
                    file['tags'] = json.loads(file['tags'])
                except:
                    file['tags'] = []
            else:
                file['tags'] = []

            # 转换datetime为字符串
            if file.get('created_at') and hasattr(file['created_at'], 'strftime'):
                file['created_at'] = file['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if file.get('updated_at') and hasattr(file['updated_at'], 'strftime'):
                file['updated_at'] = file['updated_at'].strftime('%Y-%m-%d %H:%M:%S')

        return files

    def list_files(self, user_id=None, category=None, limit=None):
        """列出文件"""
        return self.search_files(category=category, user_id=user_id, limit=limit)

    def get_file(self, file_id, user_id=None):
        """获取单个文件信息"""
        if user_id is not None:
            sql = """
                SELECT id, user_id, filename, original_name, file_path, file_size, mime_type,
                       description, tags, category, download_count, thumbnail_path, created_at, updated_at
                FROM files
                WHERE id = %s AND user_id = %s
            """
            files = self.db.query(sql, (file_id, user_id))
        else:
            sql = """
                SELECT id, user_id, filename, original_name, file_path, file_size, mime_type,
                       description, tags, category, download_count, thumbnail_path, created_at, updated_at
                FROM files
                WHERE id = %s
            """
            files = self.db.query(sql, (file_id,))

        if files:
            file = files[0]
            if file['tags']:
                try:
                    file['tags'] = json.loads(file['tags'])
                except:
                    file['tags'] = []
            else:
                file['tags'] = []

            if file.get('created_at') and hasattr(file['created_at'], 'strftime'):
                file['created_at'] = file['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if file.get('updated_at') and hasattr(file['updated_at'], 'strftime'):
                file['updated_at'] = file['updated_at'].strftime('%Y-%m-%d %H:%M:%S')

            return file
        return None

    def delete_file(self, file_id, user_id=None):
        """删除文件（包括磁盘文件和数据库记录）"""
        # 先获取文件信息
        file_info = self.get_file(file_id, user_id=user_id)
        if not file_info:
            return False

        # 删除磁盘文件
        import os
        try:
            if os.path.exists(file_info['file_path']):
                os.remove(file_info['file_path'])
                print(f"✅ 磁盘文件已删除: {file_info['file_path']}")
        except Exception as e:
            print(f"⚠️ 删除磁盘文件失败: {e}")

        # 删除数据库记录
        if user_id is not None:
            sql = "DELETE FROM files WHERE id = %s AND user_id = %s"
            self.db.execute(sql, (file_id, user_id))
        else:
            sql = "DELETE FROM files WHERE id = %s"
            self.db.execute(sql, (file_id,))

        print(f"✅ 文件记录已删除: {file_info['original_name']} (ID={file_id})")
        return True

    def batch_delete_files(self, file_ids, user_id=None):
        """批量删除文件"""
        success_count = 0
        for file_id in file_ids:
            if self.delete_file(file_id, user_id=user_id):
                success_count += 1
        return success_count

    def increment_download_count(self, file_id):
        """增加下载次数"""
        sql = "UPDATE files SET download_count = download_count + 1 WHERE id = %s"
        self.db.execute(sql, (file_id,))

    def update_file_info(self, file_id, description=None, tags=None, user_id=None):
        """更新文件信息（描述、标签）"""
        # 检查权限
        if user_id is not None:
            check_sql = "SELECT user_id FROM files WHERE id = %s"
            result = self.db.query_one(check_sql, (file_id,))
            if result and result.get('user_id') != user_id:
                return False

        updates = []
        values = []

        if description is not None:
            updates.append("description = %s")
            values.append(description)

        if tags is not None:
            updates.append("tags = %s")
            values.append(json.dumps(tags, ensure_ascii=False))

        if not updates:
            return False

        values.append(file_id)
        sql = f"UPDATE files SET {', '.join(updates)} WHERE id = %s"
        self.db.execute(sql, tuple(values))
        print(f"✅ 文件信息已更新: ID={file_id}")
        return True

    def get_user_storage_stats(self, user_id):
        """获取用户存储统计"""
        sql = """
            SELECT
                COUNT(*) as total_files,
                COALESCE(SUM(file_size), 0) as total_size,
                COUNT(CASE WHEN category = 'document' THEN 1 END) as document_count,
                COUNT(CASE WHEN category = 'image' THEN 1 END) as image_count,
                COUNT(CASE WHEN category = 'video' THEN 1 END) as video_count,
                COUNT(CASE WHEN category = 'audio' THEN 1 END) as audio_count,
                COUNT(CASE WHEN category = 'archive' THEN 1 END) as archive_count,
                COUNT(CASE WHEN category = 'other' THEN 1 END) as other_count,
                COUNT(CASE WHEN DATE(created_at) = CURDATE() THEN 1 END) as today_uploads
            FROM files
            WHERE user_id = %s
        """
        result = self.db.query_one(sql, (user_id,))

        # 确保返回有效的数据结构
        if not result:
            result = {
                'total_files': 0,
                'total_size': 0,
                'document_count': 0,
                'image_count': 0,
                'video_count': 0,
                'audio_count': 0,
                'archive_count': 0,
                'other_count': 0,
                'today_uploads': 0
            }

        # 转换 Decimal 类型为 int/float（确保 JSON 可序列化）
        total_size = int(result.get('total_size', 0) or 0)
        result['total_files'] = int(result.get('total_files', 0))
        result['total_size'] = total_size
        result['document_count'] = int(result.get('document_count', 0))
        result['image_count'] = int(result.get('image_count', 0))
        result['video_count'] = int(result.get('video_count', 0))
        result['audio_count'] = int(result.get('audio_count', 0))
        result['archive_count'] = int(result.get('archive_count', 0))
        result['other_count'] = int(result.get('other_count', 0))
        result['today_uploads'] = int(result.get('today_uploads', 0))

        # 转换总大小为可读格式
        result['total_size_mb'] = round(total_size / (1024 * 1024), 2)
        result['total_size_gb'] = round(total_size / (1024 * 1024 * 1024), 3)

        return result


class KeywordManager:
    """关键词管理器（用于AI搜索优化）"""

    def __init__(self, config_file='mysql_config.json'):
        """初始化关键词管理器"""
        self.db = MySQLManager(config_file)
        print("✅ 关键词管理器已初始化")

    def add_keyword(self, keyword, category=None, user_id=None):
        """添加关键词"""
        try:
            # 检查表是否存在，如果不存在则不执行操作
            tables = self.db.query("SHOW TABLES LIKE 'search_keywords'")
            if not tables:
                return None

            sql = """
                INSERT INTO search_keywords (keyword, category, user_id, count)
                VALUES (%s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE count = count + 1
            """
            return self.db.execute(sql, (keyword, category, user_id))
        except Exception as e:
            print(f"⚠️ 添加关键词失败: {e}")
            return None

    def get_popular_keywords(self, limit=10, user_id=None):
        """获取热门关键词"""
        try:
            # 检查表是否存在
            tables = self.db.query("SHOW TABLES LIKE 'search_keywords'")
            if not tables:
                return []

            conditions = []
            params = []

            if user_id is not None:
                conditions.append("user_id = %s")
                params.append(user_id)

            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

            sql = f"""
                SELECT keyword, category, count
                FROM search_keywords
                {where_clause}
                ORDER BY count DESC
                LIMIT {limit}
            """

            return self.db.query(sql, params if params else None)
        except Exception as e:
            print(f"⚠️ 获取关键词失败: {e}")
            return []


if __name__ == '__main__':
    # 测试数据库连接
    try:
        db = MySQLManager()
        print("✅ Database connection test successful!")
        
        # 测试查询
        result = db.query("SELECT DATABASE() as db_name")
        print(f"Current database: {result[0]['db_name']}")
        
        db.close()
    except Exception as e:
        print(f"❌ Database test failed: {e}")

