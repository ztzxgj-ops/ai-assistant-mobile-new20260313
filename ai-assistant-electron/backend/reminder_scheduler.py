#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提醒调度器 - 后台定时任务管理"""

import threading
import time
from datetime import datetime as dt
from datetime import timedelta
import json
import os
from notification_service import get_notification_service, get_notification_queue

class ReminderScheduler:
    """提醒调度器 - 在后台管理和发送提醒"""

    def __init__(self, db_manager=None, check_interval=30):
        """
        初始化调度器

        Args:
            db_manager: MySQL数据库管理器实例
            check_interval: 检查间隔（秒）
        """
        self.db = db_manager
        self.check_interval = check_interval
        self.running = False
        self.scheduler_thread = None
        self.notification_service = get_notification_service()
        self.notification_queue = get_notification_queue()
        self.active_reminders = {}  # {reminder_id: reminder_info}

    def start(self):
        """启动调度器"""
        if self.running:
            print("⚠️ 调度器已在运行")
            return False

        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True
        )
        self.scheduler_thread.start()
        print("✅ 提醒调度器已启动")
        return True

    def stop(self):
        """停止调度器"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("⏹️ 提醒调度器已停止")

    def _scheduler_loop(self):
        """调度器主循环"""
        while self.running:
            try:
                self._check_and_process_reminders()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"❌ 调度器错误: {e}")
                time.sleep(self.check_interval)

    def _check_and_process_reminders(self):
        """检查并处理待发送的提醒"""
        try:
            now = dt.now()

            # 1. 检查数据库中的提醒
            if self.db:
                self._process_db_reminders(now)

            # 2. 检查通知队列
            self._process_queued_notifications(now)

        except Exception as e:
            print(f"⚠️ 处理提醒时出错: {e}")

    def _process_db_reminders(self, now):
        """处理数据库中的提醒"""
        try:
            if not hasattr(self.db, 'execute'):
                return

            # 查询所有待处理的提醒
            reminders = self.db.query(
                """
                SELECT id, user_id, content, remind_time, status
                FROM reminders
                WHERE status = 'pending'
                AND remind_time <= %s
                LIMIT 10
                """,
                (now.isoformat(),)
            )

            for reminder in reminders:
                self._send_reminder(reminder)

        except Exception as e:
            print(f"⚠️ 处理数据库提醒失败: {e}")

    def _process_queued_notifications(self, now):
        """处理队列中的通知"""
        try:
            pending = self.notification_queue.get_pending_notifications()

            for notif in pending:
                self._send_queued_notification(notif)

        except Exception as e:
            print(f"⚠️ 处理队列通知失败: {e}")

    def _send_reminder(self, reminder):
        """发送单个提醒"""
        try:
            # 处理字典格式的提醒（从数据库DictCursor返回）
            if isinstance(reminder, dict):
                reminder_id = reminder['id']
                user_id = reminder['user_id']
                content = reminder['content']
                remind_time = reminder['remind_time']
                status = reminder['status']
            else:
                # 处理元组格式的提醒（向后兼容）
                reminder_id, user_id, content, remind_time, status = reminder

            # 显示通知
            self.notification_service.toast_notification(
                title="📢 任务提醒",
                message=content,
                timeout=10
            )

            # 更新数据库状态
            if self.db and hasattr(self.db, 'execute'):
                self.db.execute(
                    "UPDATE reminders SET status = %s, triggered = %s WHERE id = %s",
                    ('completed', 1, reminder_id)
                )

            print(f"✅ 已发送提醒: {content}")

        except Exception as e:
            print(f"❌ 发送提醒失败: {e}")

    def _send_queued_notification(self, notification):
        """发送队列中的通知"""
        try:
            self.notification_service.toast_notification(
                title=notification['title'],
                message=notification['message'],
                timeout=10
            )

            notification['status'] = 'sent'
            notification['delivered_at'] = dt.now().isoformat()
            print(f"✅ 已发送通知: {notification['title']}")

        except Exception as e:
            print(f"❌ 发送通知失败: {e}")

    def add_reminder(self, user_id, message, remind_time, remind_type='once'):
        """
        添加提醒

        Args:
            user_id: 用户ID
            message: 提醒信息
            remind_time: 提醒时间 (datetime或时间戳字符串)
            remind_type: 提醒类型 ('once' - 一次性, 'daily' - 每天, 'weekly' - 每周)

        Returns:
            dict: 提醒对象或错误
        """
        try:
            if isinstance(remind_time, str):
                remind_time = dt.fromisoformat(remind_time)

            reminder_info = {
                'user_id': user_id,
                'message': message,
                'remind_time': remind_time.isoformat(),
                'type': remind_type,
                'status': 'pending',
                'created_at': dt.now().isoformat()
            }

            # 保存到数据库（如果可用）
            if self.db and hasattr(self.db, 'execute'):
                try:
                    self.db.execute(
                        """
                        INSERT INTO reminders
                        (user_id, content, remind_time, status, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (user_id, message, remind_time.isoformat(), 'pending', dt.now().isoformat())
                    )
                except Exception as e:
                    print(f"⚠️ 保存提醒到数据库失败: {e}")
                    print(f"⚠️ 提醒内容: user_id={user_id}, message={message}, time={remind_time}")

            # 也保存到活动提醒字典
            reminder_id = len(self.active_reminders) + 1
            reminder_info['id'] = reminder_id
            self.active_reminders[reminder_id] = reminder_info

            return {'status': 'success', 'reminder': reminder_info}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def cancel_reminder(self, reminder_id, user_id=None):
        """
        取消提醒

        Args:
            reminder_id: 提醒ID
            user_id: 用户ID（用于验证权限）

        Returns:
            bool: 是否成功
        """
        try:
            if reminder_id in self.active_reminders:
                reminder = self.active_reminders[reminder_id]

                # 验证权限
                if user_id and reminder.get('user_id') != user_id:
                    return False

                del self.active_reminders[reminder_id]

            # 更新数据库
            if self.db and hasattr(self.db, 'execute'):
                try:
                    self.db.execute(
                        "UPDATE reminders SET status = %s WHERE id = %s",
                        ('cancelled', reminder_id)
                    )
                except:
                    pass

            return True

        except Exception as e:
            print(f"❌ 取消提醒失败: {e}")
            return False

    def list_reminders(self, user_id=None):
        """
        列出提醒

        Args:
            user_id: 用户ID（可选，为空则返回所有）

        Returns:
            list: 提醒列表
        """
        try:
            reminders = []

            # 从活动提醒字典获取
            for reminder_id, reminder in self.active_reminders.items():
                if user_id is None or reminder.get('user_id') == user_id:
                    reminders.append(reminder)

            # 从数据库获取（如果可用）
            if self.db and hasattr(self.db, 'execute'):
                try:
                    db_reminders = self.db.query(
                        """
                        SELECT id, user_id, content, remind_time, status
                        FROM reminders
                        WHERE status IN ('pending', 'completed')
                        AND user_id = %s
                        ORDER BY remind_time DESC
                        """,
                        (user_id,) if user_id else (0,)
                    )

                    for db_reminder in db_reminders:
                        reminder_dict = {
                            'id': db_reminder[0],
                            'user_id': db_reminder[1],
                            'message': db_reminder[2],
                            'remind_time': db_reminder[3],
                            'status': db_reminder[4]
                        }
                        reminders.append(reminder_dict)
                except:
                    pass

            return reminders

        except Exception as e:
            print(f"❌ 获取提醒列表失败: {e}")
            return []

    def parse_reminder_time(self, time_string):
        """
        解析提醒时间字符串

        Args:
            time_string: 时间字符串 (例如: "明天 14:30", "下周一 09:00", "1小时后")

        Returns:
            datetime: 解析后的时间或None
        """
        now = dt.now()
        lower_str = time_string.lower()

        try:
            # 处理相对时间
            if '小时后' in lower_str:
                hours = int(''.join(filter(str.isdigit, time_string.split('小时')[0])) or 1)
                return now + timedelta(hours=hours)

            if '分钟后' in lower_str:
                minutes = int(''.join(filter(str.isdigit, time_string.split('分钟')[0])) or 1)
                return now + timedelta(minutes=minutes)

            if '秒后' in lower_str or '秒钟后' in lower_str:
                seconds = int(''.join(filter(str.isdigit, time_string.split('秒')[0])) or 1)
                return now + timedelta(seconds=seconds)

            # 处理绝对时间
            if '明天' in lower_str:
                target_date = (now + timedelta(days=1)).date()
                time_part = '09:00'
                if '14:' in time_string or '14:30' in time_string:
                    time_part = '14:30'
                elif ':' in time_string:
                    # 提取时间部分
                    import re
                    match = re.search(r'(\d{1,2}):(\d{2})', time_string)
                    if match:
                        time_part = match.group(0)

                return dt.combine(target_date, dt.strptime(time_part, '%H:%M').time())

            if '后天' in lower_str:
                target_date = (now + timedelta(days=2)).date()
                return dt.combine(target_date, dt.strptime('09:00', '%H:%M').time())

            # 如果是ISO格式时间戳，直接解析
            if 'T' in time_string:
                return dt.fromisoformat(time_string)

            # 如果都不匹配，返回None
            return None

        except Exception as e:
            print(f"⚠️ 时间解析失败: {e}")
            return None


# 全局实例
_global_scheduler = None

def get_global_scheduler(db_manager=None):
    """获取全局调度器实例"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = ReminderScheduler(db_manager=db_manager)
    return _global_scheduler
