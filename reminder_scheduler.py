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

# 导入 WebSocket 服务器
try:
    from websocket_server import get_websocket_server
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("⚠️ WebSocket 模块未安装，将不支持移动端推送")

# 导入 FCM 推送服务
try:
    from fcm_push_service import get_fcm_service
    from mysql_manager import DeviceTokenManager
    FCM_AVAILABLE = True
except ImportError:
    FCM_AVAILABLE = False
    print("⚠️ FCM 模块未安装，将不支持推送通知")

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

        # 初始化 WebSocket 服务器
        self.ws_server = None
        if WEBSOCKET_AVAILABLE:
            try:
                self.ws_server = get_websocket_server()
                print("✅ WebSocket 服务器已初始化")
            except Exception as e:
                print(f"⚠️ WebSocket 服务器初始化失败: {e}")

        # 初始化 FCM 推送服务
        self.fcm_service = None
        self.device_token_manager = None
        if FCM_AVAILABLE:
            try:
                self.fcm_service = get_fcm_service()
                if self.db:
                    self.device_token_manager = DeviceTokenManager(self.db)
                print("✅ FCM 推送服务已初始化")
            except Exception as e:
                print(f"⚠️ FCM 推送服务初始化失败: {e}")

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

        # 启动 WebSocket 服务器
        if self.ws_server:
            try:
                self.ws_server.start()
            except Exception as e:
                print(f"⚠️ WebSocket 服务器启动失败: {e}")

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
            if not self.db:
                return

            if not hasattr(self.db, 'execute'):
                return

            # 格式化当前时间为数据库格式（YYYY-MM-DD HH:MM:SS）
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')
            print(f"🕐 [调度器] 当前时间: {now_str}")

            # 查询所有待处理的提醒（包含好友提醒相关字段）
            # 注意：使用 datetime 对象而不是字符串，避免 pymysql 参数绑定问题
            print(f"🔍 [调度器] 准备查询，now类型: {type(now)}, 值: {now}")

            try:
                reminders = self.db.query(
                    """
                    SELECT r.id, r.user_id, r.content, r.remind_time, r.status, r.repeat_type,
                           r.is_friend_reminder, r.creator_id, u.username AS creator_name
                    FROM reminders r
                    LEFT JOIN users u ON r.creator_id = u.id
                    WHERE r.status = 'pending'
                    AND r.triggered = 0
                    AND r.remind_time <= %s
                    LIMIT 10
                    """,
                    (now,)  # 传递 datetime 对象而不是字符串
                )
                print(f"🔍 [调度器] 查询成功，结果类型: {type(reminders)}, 长度: {len(reminders) if reminders else 0}")
            except Exception as query_ex:
                print(f"❌ [调度器] 查询异常: {query_ex}")
                import traceback
                traceback.print_exc()
                reminders = []

            print(f"🔍 [调度器] 查询到 {len(reminders)} 个待处理提醒")
            for reminder in reminders:
                print(f"  📋 ID:{reminder['id']}, 内容:{reminder['content']}, 计划时间:{reminder['remind_time']}")

            for reminder in reminders:
                self._send_reminder(reminder)

        except Exception as e:
            print(f"⚠️ 处理数据库提醒失败: {e}")
            import traceback
            traceback.print_exc()

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
                repeat_type = reminder.get('repeat_type', 'once')
                is_friend_reminder = reminder.get('is_friend_reminder', 0)
                creator_name = reminder.get('creator_name', '')
            else:
                # 处理元组格式的提醒（向后兼容）
                if len(reminder) >= 6:
                    reminder_id, user_id, content, remind_time, status, repeat_type = reminder[:6]
                else:
                    reminder_id, user_id, content, remind_time, status = reminder[:5]
                    repeat_type = 'once'
                is_friend_reminder = 0
                creator_name = ''

            # 🔒 关键修复：立即标记triggered=1，防止重复触发
            if self.db and hasattr(self.db, 'execute'):
                self.db.execute(
                    "UPDATE reminders SET triggered = 1 WHERE id = %s AND triggered = 0",
                    (reminder_id,)
                )
                print(f"🔒 已锁定提醒 ID:{reminder_id}，防止重复触发")

            # 根据是否为好友提醒设置不同的标题
            if is_friend_reminder == 1 and creator_name:
                title = f"📢 来自 {creator_name} 的提醒"
            else:
                title = "📢 任务提醒"

            # 获取用户的声音设置
            sound_type = 'default'
            volume = 0.7
            try:
                if self.db and hasattr(self.db, 'query'):
                    settings = self.db.query(
                        "SELECT setting_key, setting_value FROM user_settings WHERE user_id = %s AND setting_key IN ('reminder_sound_type', 'reminder_sound_volume')",
                        (user_id,)
                    )
                    for setting in settings:
                        if setting['setting_key'] == 'reminder_sound_type':
                            sound_type = setting['setting_value']
                        elif setting['setting_key'] == 'reminder_sound_volume':
                            volume = float(setting['setting_value'])
            except Exception as e:
                print(f"⚠️ 读取用户声音设置失败，使用默认值: {e}")

            # 1. 发送本地通知（桌面端）
            self.notification_service.toast_notification(
                title=title,
                message=content,
                timeout=10,
                sound_type=sound_type,
                volume=volume
            )

            # 2. 通过 WebSocket 推送到移动端 - 已禁用，改用本地通知
            # print(f"🔍 DEBUG: 准备推送 WebSocket, ws_server={self.ws_server}, user_id={user_id}")
            # if self.ws_server:
            #     try:
            #         print(f"🔍 DEBUG: 调用 send_reminder, user_id={user_id}, content={content}")
            #         result = self.ws_server.send_reminder(user_id, {
            #             'id': reminder_id,
            #             'content': content,
            #             'remind_time': str(remind_time),
            #             'is_friend_reminder': is_friend_reminder,
            #             'creator_name': creator_name,
            #             'title': title,
            #             'repeat_type': repeat_type  # 添加循环类型字段
            #         })
            #         print(f"🔍 DEBUG: send_reminder 返回值={result}")
            #     except Exception as e:
            #         print(f"⚠️ WebSocket 推送失败: {e}")
            #         import traceback
            #         traceback.print_exc()
            # else:
            #     print(f"⚠️ ws_server 为 None，无法推送")
            print(f"ℹ️ WebSocket推送已禁用，移动端使用本地通知")

            # 3. 通过 FCM 推送到移动端（支持后台通知）- 已禁用，改用本地通知
            # if self.fcm_service and self.device_token_manager:
            #     try:
            #         # 获取用户的所有活跃设备token
            #         devices = self.device_token_manager.get_user_device_tokens(user_id, active_only=True)
            #
            #         if devices:
            #             device_tokens = [d['device_token'] for d in devices]
            #             print(f"📱 准备发送FCM推送到 {len(device_tokens)} 个设备")
            #
            #             # 发送FCM推送通知（使用自定义标题）
            #             result = self.fcm_service.send_reminder_notification(
            #                 device_tokens=device_tokens,
            #                 reminder_content=content,
            #                 reminder_id=reminder_id,
            #                 title=title
            #             )
            #
            #             if result.get('success') or result.get('success_count', 0) > 0:
            #                 print(f"✅ FCM推送成功: {result}")
            #             else:
            #                 print(f"⚠️ FCM推送失败: {result}")
            #         else:
            #             print(f"⚠️ 用户 {user_id} 没有注册的设备token")
            #
            #     except Exception as e:
            #         print(f\"❌ FCM推送失败: {e}\")\n            #         import traceback
            #         traceback.print_exc()
            print(f"ℹ️ FCM推送已禁用，移动端使用本地通知")

            # 4. 更新数据库状态（根据提醒类型）
            if self.db and hasattr(self.db, 'execute'):
                # 如果是循环提醒，计算下一次提醒时间并更新
                if repeat_type in ['minutely', 'every_5_minutes', 'every_10_minutes', 'every_30_minutes', 'hourly', 'daily', 'weekly', 'monthly', 'yearly']:
                    next_remind_time = self._calculate_next_remind_time(remind_time, repeat_type)
                    if next_remind_time:
                        # 更新为下一次提醒时间，保持pending状态，重置triggered=0
                        self.db.execute(
                            "UPDATE reminders SET remind_time = %s, status = 'pending', triggered = 0 WHERE id = %s",
                            (next_remind_time, reminder_id)
                        )
                        print(f"🔄 循环提醒已更新，下次提醒时间: {next_remind_time}")
                    else:
                        # 计算失败，标记为completed
                        self.db.execute(
                            "UPDATE reminders SET status = %s, triggered = %s WHERE id = %s",
                            ('completed', 1, reminder_id)
                        )
                # 单次提醒：triggered已在前面设置为1，这里不需要再更新
                # 等待用户手动标记完成或删除

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

    def _calculate_next_remind_time(self, current_time, repeat_type):
        """
        计算下一次提醒时间

        Args:
            current_time: 当前提醒时间（datetime或字符串）
            repeat_type: 循环类型（'daily', 'weekly', 'monthly', 'yearly'）

        Returns:
            datetime: 下一次提醒时间，如果计算失败返回None
        """
        try:
            # 确保current_time是datetime对象
            if isinstance(current_time, str):
                current_time = dt.fromisoformat(current_time.replace('Z', '+00:00'))
            elif not isinstance(current_time, dt):
                # 如果是其他类型（如date），转换为datetime
                current_time = dt.combine(current_time, dt.min.time())

            # 根据repeat_type计算下一次时间
            if repeat_type == 'minutely':
                # 每分钟：加1分钟
                next_time = current_time + timedelta(minutes=1)
            elif repeat_type == 'every_5_minutes':
                # 每5分钟：加5分钟
                next_time = current_time + timedelta(minutes=5)
            elif repeat_type == 'every_10_minutes':
                # 每10分钟：加10分钟
                next_time = current_time + timedelta(minutes=10)
            elif repeat_type == 'every_30_minutes':
                # 每30分钟：加30分钟
                next_time = current_time + timedelta(minutes=30)
            elif repeat_type == 'hourly':
                # 每小时：加1小时
                next_time = current_time + timedelta(hours=1)
            elif repeat_type == 'daily':
                # 每天：加1天
                next_time = current_time + timedelta(days=1)
            elif repeat_type == 'weekly':
                # 每周：加7天
                next_time = current_time + timedelta(days=7)
            elif repeat_type == 'monthly':
                # 每月：加1个月（处理月末情况）
                year = current_time.year
                month = current_time.month + 1
                if month > 12:
                    year += 1
                    month = 1
                day = current_time.day
                # 处理月末日期（如1月31日 -> 2月28日）
                import calendar
                max_day = calendar.monthrange(year, month)[1]
                if day > max_day:
                    day = max_day
                next_time = dt(year, month, day, current_time.hour, current_time.minute)
            elif repeat_type == 'yearly':
                # 每年：加1年
                year = current_time.year + 1
                month = current_time.month
                day = current_time.day
                # 处理闰年2月29日的情况
                if month == 2 and day == 29:
                    import calendar
                    if not calendar.isleap(year):
                        day = 28
                next_time = dt(year, month, day, current_time.hour, current_time.minute)
            else:
                print(f"⚠️ 未知的循环类型: {repeat_type}")
                return None

            return next_time

        except Exception as e:
            print(f"❌ 计算下一次提醒时间失败: {e}")
            import traceback
            traceback.print_exc()
            return None

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
                        (user_id, content, remind_time, status, triggered, created_at)
                        VALUES (%s, %s, %s, %s, 0, %s)
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

    def _adjust_hour_by_period(self, time_string, hour):
        """
        根据时间段关键词调整小时数

        Args:
            time_string: 原始时间字符串
            hour: 提取的小时数(1-12或0-23)

        Returns:
            调整后的小时数(0-23)
        """
        lower_str = time_string.lower()

        # 下午时段: 12:00-17:59 (如果输入1-6点,转为13-18点)
        if any(word in lower_str for word in ['下午', 'pm', 'p.m.']):
            if 1 <= hour <= 6:
                return hour + 12
            elif hour == 12:
                return 12
            else:
                return hour

        # 晚上时段: 18:00-23:59 (如果输入1-11点,转为19-23点或18点)
        elif any(word in lower_str for word in ['晚上', '晚', '夜里', '夜间']):
            if 1 <= hour <= 5:
                return hour + 18  # 晚上1点=19点, 晚上5点=23点
            elif hour == 6:
                return 18  # 晚上6点=18点
            elif 7 <= hour <= 11:
                return hour + 12  # 晚上7点=19点
            else:
                return hour

        # 凌晨时段: 00:00-05:59
        elif any(word in lower_str for word in ['凌晨', '半夜', '深夜']):
            if hour >= 12:
                return hour - 12  # 凌晨12点=0点
            else:
                return hour

        # 早上/上午时段: 06:00-11:59
        elif any(word in lower_str for word in ['早上', '上午', '早晨', '清晨', 'am', 'a.m.']):
            if hour == 12:
                return 0  # 上午12点=0点
            elif hour > 12:
                return hour - 12
            else:
                return hour

        # 中午: 11:00-13:00
        elif any(word in lower_str for word in ['中午', '正午']):
            if hour < 11:
                return 12  # 默认中午12点
            else:
                return hour

        # 没有时间段关键词,根据小时数智能判断
        else:
            # 如果是1-6点且没有明确上下午,可能是下午
            # 但为了避免误判,保持原样
            return hour

    def parse_reminder_time(self, time_string):
        """
        解析提醒时间字符串

        Args:
            time_string: 时间字符串 (例如: "明天 14:30", "12月28日16:00", "每年10月30日9:31")

        Returns:
            tuple: (datetime, recurrence_type)
                   recurrence_type可以是: None, 'yearly', 'monthly', 'weekly'
                   如果是循环提醒，datetime是下一次触发的时间
        """
        now = dt.now()
        lower_str = time_string.lower()
        import re

        try:
            # 处理循环提醒格式（新增）
            # 每年X月X日X:X
            match = re.search(r'每年\s*(\d{1,2})月(\d{1,2})日\s*(\d{1,2})\s*:\s*(\d{1,2})', time_string)
            if match:
                month, day, hour, minute = map(int, match.groups())
                year = now.year
                # 计算下一次触发时间
                next_trigger = dt(year, month, day, hour, minute)
                if next_trigger <= now:
                    next_trigger = dt(year + 1, month, day, hour, minute)
                return (next_trigger, 'yearly')

            # 每年X月X日X点X分
            match = re.search(r'每年\s*(\d{1,2})月(\d{1,2})日\s*(\d{1,2})点(\d{1,2})分', time_string)
            if match:
                month, day, hour, minute = map(int, match.groups())
                year = now.year
                next_trigger = dt(year, month, day, hour, minute)
                if next_trigger <= now:
                    next_trigger = dt(year + 1, month, day, hour, minute)
                return (next_trigger, 'yearly')

            # 每年X月X日X点
            match = re.search(r'每年\s*(\d{1,2})月(\d{1,2})日\s*(\d{1,2})点', time_string)
            if match:
                month, day, hour = map(int, match.groups())
                year = now.year
                next_trigger = dt(year, month, day, hour, 0)
                if next_trigger <= now:
                    next_trigger = dt(year + 1, month, day, hour, 0)
                return (next_trigger, 'yearly')

            # 每年X月X日（默认9:00）
            match = re.search(r'每年\s*(\d{1,2})月(\d{1,2})日', time_string)
            if match:
                month, day = map(int, match.groups())
                year = now.year
                next_trigger = dt(year, month, day, 9, 0)
                if next_trigger <= now:
                    next_trigger = dt(year + 1, month, day, 9, 0)
                return (next_trigger, 'yearly')

            # 每月X日X:X
            match = re.search(r'每月\s*(\d{1,2})日\s*(\d{1,2})\s*:\s*(\d{1,2})', time_string)
            if match:
                day, hour, minute = map(int, match.groups())
                year, month = now.year, now.month
                next_trigger = dt(year, month, day, hour, minute)
                if next_trigger <= now:
                    # 下个月
                    if month == 12:
                        next_trigger = dt(year + 1, 1, day, hour, minute)
                    else:
                        next_trigger = dt(year, month + 1, day, hour, minute)
                return (next_trigger, 'monthly')

            # 每月X日X点X分
            match = re.search(r'每月\s*(\d{1,2})日\s*(\d{1,2})点(\d{1,2})分', time_string)
            if match:
                day, hour, minute = map(int, match.groups())
                year, month = now.year, now.month
                next_trigger = dt(year, month, day, hour, minute)
                if next_trigger <= now:
                    if month == 12:
                        next_trigger = dt(year + 1, 1, day, hour, minute)
                    else:
                        next_trigger = dt(year, month + 1, day, hour, minute)
                return (next_trigger, 'monthly')

            # 每月X日X点
            match = re.search(r'每月\s*(\d{1,2})日\s*(\d{1,2})点', time_string)
            if match:
                day, hour = map(int, match.groups())
                year, month = now.year, now.month
                next_trigger = dt(year, month, day, hour, 0)
                if next_trigger <= now:
                    if month == 12:
                        next_trigger = dt(year + 1, 1, day, hour, 0)
                    else:
                        next_trigger = dt(year, month + 1, day, hour, 0)
                return (next_trigger, 'monthly')

            # 每月X日（默认9:00）
            match = re.search(r'每月\s*(\d{1,2})日', time_string)
            if match:
                day = int(match.group(1))
                year, month = now.year, now.month
                next_trigger = dt(year, month, day, 9, 0)
                if next_trigger <= now:
                    if month == 12:
                        next_trigger = dt(year + 1, 1, day, 9, 0)
                    else:
                        next_trigger = dt(year, month + 1, day, 9, 0)
                return (next_trigger, 'monthly')

            # 每周X（支持中文）
            weekday_map = {'一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6}

            # 每周X X:X
            match = re.search(r'每周([一二三四五六日天])\s*(\d{1,2})\s*:\s*(\d{1,2})', time_string)
            if match:
                weekday_str, hour, minute = match.groups()
                target_weekday = weekday_map[weekday_str]
                hour, minute = int(hour), int(minute)

                # 计算下一个该星期几
                days_ahead = target_weekday - now.weekday()
                if days_ahead < 0 or (days_ahead == 0 and now.time() >= dt(now.year, now.month, now.day, hour, minute).time()):
                    days_ahead += 7
                next_trigger = now + timedelta(days=days_ahead)
                next_trigger = dt(next_trigger.year, next_trigger.month, next_trigger.day, hour, minute)
                return (next_trigger, 'weekly')

            # 每周X X点X分
            match = re.search(r'每周([一二三四五六日天])\s*(\d{1,2})点(\d{1,2})分', time_string)
            if match:
                weekday_str, hour, minute = match.groups()
                target_weekday = weekday_map[weekday_str]
                hour, minute = int(hour), int(minute)

                days_ahead = target_weekday - now.weekday()
                if days_ahead < 0 or (days_ahead == 0 and now.time() >= dt(now.year, now.month, now.day, hour, minute).time()):
                    days_ahead += 7
                next_trigger = now + timedelta(days=days_ahead)
                next_trigger = dt(next_trigger.year, next_trigger.month, next_trigger.day, hour, minute)
                return (next_trigger, 'weekly')

            # 每周X X点
            match = re.search(r'每周([一二三四五六日天])\s*(\d{1,2})点', time_string)
            if match:
                weekday_str, hour = match.groups()
                target_weekday = weekday_map[weekday_str]
                hour = int(hour)

                days_ahead = target_weekday - now.weekday()
                if days_ahead < 0 or (days_ahead == 0 and now.time() >= dt(now.year, now.month, now.day, hour, 0).time()):
                    days_ahead += 7
                next_trigger = now + timedelta(days=days_ahead)
                next_trigger = dt(next_trigger.year, next_trigger.month, next_trigger.day, hour, 0)
                return (next_trigger, 'weekly')

            # 每周X（默认9:00）
            match = re.search(r'每周([一二三四五六日天])', time_string)
            if match:
                weekday_str = match.group(1)
                target_weekday = weekday_map[weekday_str]

                days_ahead = target_weekday - now.weekday()
                if days_ahead < 0 or (days_ahead == 0 and now.time() >= dt(now.year, now.month, now.day, 9, 0).time()):
                    days_ahead += 7
                next_trigger = now + timedelta(days=days_ahead)
                next_trigger = dt(next_trigger.year, next_trigger.month, next_trigger.day, 9, 0)
                return (next_trigger, 'weekly')

            # 每天/每日（新增）
            # 每天X:X
            match = re.search(r'每[天日]\s*(\d{1,2})\s*:\s*(\d{1,2})', time_string)
            if match:
                hour, minute = map(int, match.groups())
                # 如果今天的该时间还没到，就是今天；否则是明天
                target_time = dt(now.year, now.month, now.day, hour, minute)
                if target_time <= now:
                    target_time = target_time + timedelta(days=1)
                return (target_time, 'daily')

            # 每天X点X分（允许中间有其他词，如"每天早上9点30分"）
            match = re.search(r'每[天日].*?(\d{1,2})点(\d{1,2})分', time_string)
            if match:
                hour, minute = map(int, match.groups())
                target_time = dt(now.year, now.month, now.day, hour, minute)
                if target_time <= now:
                    target_time = target_time + timedelta(days=1)
                return (target_time, 'daily')

            # 每天X点（允许中间有其他词，如"每天早上9点"）
            match = re.search(r'每[天日].*?(\d{1,2})点', time_string)
            if match:
                hour = int(match.group(1))
                target_time = dt(now.year, now.month, now.day, hour, 0)
                if target_time <= now:
                    target_time = target_time + timedelta(days=1)
                return (target_time, 'daily')

            # 每天（默认9:00）
            match = re.search(r'每[天日]', time_string)
            if match:
                target_time = dt(now.year, now.month, now.day, 9, 0)
                if target_time <= now:
                    target_time = target_time + timedelta(days=1)
                return (target_time, 'daily')

            # 非循环提醒的处理（返回元组格式以保持一致性）
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

            # 处理具体日期格式（新增）
            # 格式: 2025年12月28日16:00
            match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})\s*:\s*(\d{1,2})', time_string)
            if match:
                year, month, day, hour, minute = map(int, match.groups())
                return dt(year, month, day, hour, minute)

            # 格式: 2025-12-28 16:00
            match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2})\s*:\s*(\d{1,2})', time_string)
            if match:
                year, month, day, hour, minute = map(int, match.groups())
                return dt(year, month, day, hour, minute)

            # 格式: 12月28日16:00 或 12月28日 16:00
            match = re.search(r'(\d{1,2})月(\d{1,2})日\s*(\d{1,2})\s*:\s*(\d{1,2})', time_string)
            if match:
                month, day, hour, minute = map(int, match.groups())
                year = now.year
                # 如果指定的月份小于当前月份，说明是明年
                if month < now.month or (month == now.month and day < now.day):
                    year += 1
                return dt(year, month, day, hour, minute)

            # 格式: 12月28日16点30分 或 12月28日下午6点30分
            match = re.search(r'(\d{1,2})月(\d{1,2})日.{0,4}?(?:上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点(\d{1,2})分', time_string)
            if match:
                month, day, hour, minute = map(int, match.groups())
                # 处理时间段修正
                hour = self._adjust_hour_by_period(time_string, hour)
                year = now.year
                if month < now.month or (month == now.month and day < now.day):
                    year += 1
                return dt(year, month, day, hour, minute)

            # 格式: 12月28日16点 或 12月28日下午6点
            match = re.search(r'(\d{1,2})月(\d{1,2})日.{0,4}?(?:上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点', time_string)
            if match:
                month, day, hour = map(int, match.groups())
                # 处理时间段修正
                hour = self._adjust_hour_by_period(time_string, hour)
                year = now.year
                if month < now.month or (month == now.month and day < now.day):
                    year += 1
                return dt(year, month, day, hour, 0)

            # 格式: 12月28日（默认09:00）
            match = re.search(r'(\d{1,2})月(\d{1,2})日', time_string)
            if match:
                month, day = map(int, match.groups())
                year = now.year
                if month < now.month or (month == now.month and day < now.day):
                    year += 1
                return dt(year, month, day, 9, 0)

            # 处理绝对时间
            # 今天
            if '今天' in lower_str or '今日' in lower_str:
                target_date = now.date()
                time_part = '09:00'
                import re

                # 优先匹配"X点X分"格式（如"11点5分"、"下午3点30分"）
                if '点' in time_string:
                    match = re.search(r'(\d{1,2})点(\d{1,2})分', time_string)
                    if match:
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        # 处理时间段修正
                        hour = self._adjust_hour_by_period(time_string, hour)
                        time_part = f'{hour:02d}:{minute:02d}'
                    else:
                        # 匹配"X点半"格式
                        match = re.search(r'(\d{1,2})点半', time_string)
                        if match:
                            hour = int(match.group(1))
                            # 处理时间段修正
                            hour = self._adjust_hour_by_period(time_string, hour)
                            time_part = f'{hour:02d}:30'
                        else:
                            # 匹配"X点"格式（如"11点"、"今天下午3点"）
                            match = re.search(r'(\d{1,2})点', time_string)
                            if match:
                                hour = int(match.group(1))
                                # 处理时间段修正
                                hour = self._adjust_hour_by_period(time_string, hour)
                                time_part = f'{hour:02d}:00'
                # 其次匹配冒号格式（如"11:05"或"14: 00"，允许空格）
                elif ':' in time_string:
                    match = re.search(r'(\d{1,2})\s*:\s*(\d{1,2})', time_string)
                    if match:
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        # 处理时间段修正
                        hour = self._adjust_hour_by_period(time_string, hour)
                        time_part = f'{hour:02d}:{minute:02d}'

                return dt.combine(target_date, dt.strptime(time_part, '%H:%M').time())

            if '明天' in lower_str:
                target_date = (now + timedelta(days=1)).date()
                time_part = '09:00'
                import re

                # 优先匹配"X点X分"格式（如"11点5分"、"明天下午3点30分"）
                if '点' in time_string:
                    match = re.search(r'(\d{1,2})点(\d{1,2})分', time_string)
                    if match:
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        # 处理时间段修正
                        hour = self._adjust_hour_by_period(time_string, hour)
                        time_part = f'{hour:02d}:{minute:02d}'
                    else:
                        # 匹配"X点半"格式
                        match = re.search(r'(\d{1,2})点半', time_string)
                        if match:
                            hour = int(match.group(1))
                            # 处理时间段修正
                            hour = self._adjust_hour_by_period(time_string, hour)
                            time_part = f'{hour:02d}:30'
                        else:
                            # 匹配"X点"格式（如"11点"、"明天下午4点"）
                            match = re.search(r'(\d{1,2})点', time_string)
                            if match:
                                hour = int(match.group(1))
                                # 处理时间段修正
                                hour = self._adjust_hour_by_period(time_string, hour)
                                time_part = f'{hour:02d}:00'
                # 其次匹配冒号格式（如"11:05"或"14: 00"，允许空格）
                elif ':' in time_string:
                    match = re.search(r'(\d{1,2})\s*:\s*(\d{1,2})', time_string)
                    if match:
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        # 处理时间段修正
                        hour = self._adjust_hour_by_period(time_string, hour)
                        time_part = f'{hour:02d}:{minute:02d}'

                return dt.combine(target_date, dt.strptime(time_part, '%H:%M').time())

            if '后天' in lower_str:
                target_date = (now + timedelta(days=2)).date()
                time_part = '09:00'
                import re

                # 优先匹配"X点X分"格式（如"11点5分"、"后天下午3点30分"）
                if '点' in time_string:
                    match = re.search(r'(\d{1,2})点(\d{1,2})分', time_string)
                    if match:
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        # 处理时间段修正
                        hour = self._adjust_hour_by_period(time_string, hour)
                        time_part = f'{hour:02d}:{minute:02d}'
                    else:
                        # 匹配"X点半"格式
                        match = re.search(r'(\d{1,2})点半', time_string)
                        if match:
                            hour = int(match.group(1))
                            # 处理时间段修正
                            hour = self._adjust_hour_by_period(time_string, hour)
                            time_part = f'{hour:02d}:30'
                        else:
                            # 匹配"X点"格式（如"11点"、"后天晚上8点"）
                            match = re.search(r'(\d{1,2})点', time_string)
                            if match:
                                hour = int(match.group(1))
                                # 处理时间段修正
                                hour = self._adjust_hour_by_period(time_string, hour)
                                time_part = f'{hour:02d}:00'
                # 其次匹配冒号格式（如"11:05"或"14: 00"，允许空格）
                elif ':' in time_string:
                    match = re.search(r'(\d{1,2})\s*:\s*(\d{1,2})', time_string)
                    if match:
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        # 处理时间段修正
                        hour = self._adjust_hour_by_period(time_string, hour)
                        time_part = f'{hour:02d}:{minute:02d}'

                return dt.combine(target_date, dt.strptime(time_part, '%H:%M').time())

            # 单独时间格式（默认为今天）
            # 注意：这个要放在"今天/明天/后天"之后，避免误匹配
            # 如果没有明确日期，且包含时间，默认为今天
            if '今天' not in lower_str and '明天' not in lower_str and '后天' not in lower_str:
                target_date = now.date()
                time_part = None
                import re

                # 匹配"X点X分"格式（如"10点30分"、"下午3点30分"）
                match = re.search(r'^.*?(\d{1,2})点(\d{1,2})分', time_string)
                if match:
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    # 处理时间段修正(下午/晚上/PM等)
                    hour = self._adjust_hour_by_period(time_string, hour)
                    time_part = f'{hour:02d}:{minute:02d}'
                else:
                    # 匹配"X点半"格式
                    match = re.search(r'^.*?(\d{1,2})点半', time_string)
                    if match:
                        hour = int(match.group(1))
                        # 处理时间段修正
                        hour = self._adjust_hour_by_period(time_string, hour)
                        time_part = f'{hour:02d}:30'
                    else:
                        # 匹配"X点"格式（如"10点"、"下午3点"）
                        match = re.search(r'^.*?(\d{1,2})点', time_string)
                        if match:
                            hour = int(match.group(1))
                            # 处理时间段修正
                            hour = self._adjust_hour_by_period(time_string, hour)
                            time_part = f'{hour:02d}:00'
                        else:
                            # 匹配冒号格式（如"10:30"）
                            match = re.search(r'^.*?(\d{1,2})\s*:\s*(\d{1,2})', time_string)
                            if match:
                                hour = int(match.group(1))
                                minute = int(match.group(2))
                                # 处理时间段修正
                                hour = self._adjust_hour_by_period(time_string, hour)
                                time_part = f'{hour:02d}:{minute:02d}'

                if time_part:
                    return dt.combine(target_date, dt.strptime(time_part, '%H:%M').time())

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
