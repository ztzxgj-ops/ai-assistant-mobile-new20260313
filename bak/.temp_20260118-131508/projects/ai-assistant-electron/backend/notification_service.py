#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""系统通知服务 - 跨平台提醒功能"""

import os
import sys
import json
import datetime
from datetime import datetime as dt
from pathlib import Path

class NotificationService:
    """系统通知服务"""

    def __init__(self):
        self.platform = sys.platform
        self.callbacks = []

    def add_callback(self, callback):
        """添加通知回调函数"""
        self.callbacks.append(callback)

    def notify(self, title, message, urgency='normal'):
        """
        显示系统通知

        Args:
            title: 通知标题
            message: 通知内容
            urgency: 紧急级别 ('low', 'normal', 'critical')

        Returns:
            bool: 是否成功发送通知
        """
        try:
            if self.platform == 'darwin':  # macOS
                return self._notify_macos(title, message, urgency)
            elif self.platform == 'linux':  # Linux
                return self._notify_linux(title, message, urgency)
            elif self.platform == 'win32':  # Windows
                return self._notify_windows(title, message, urgency)
            else:
                print(f"⚠️ 不支持的平台: {self.platform}")
                return False
        except Exception as e:
            print(f"❌ 通知发送失败: {e}")
            return False

    def _notify_macos(self, title, message, urgency):
        """macOS 通知（使用AppleScript）"""
        try:
            # 使用 AppleScript 显示通知
            apple_script = f'''
            display notification "{message}" with title "{title}"
            '''
            os.system(f"osascript -e '{apple_script}'")

            # 执行回调
            for callback in self.callbacks:
                try:
                    callback({'type': 'notification', 'title': title, 'message': message})
                except:
                    pass

            return True
        except Exception as e:
            print(f"macOS 通知失败: {e}")
            return False

    def _notify_linux(self, title, message, urgency):
        """Linux 通知（使用 notify-send）"""
        try:
            urgency_map = {'low': 'low', 'normal': 'normal', 'critical': 'critical'}
            cmd = f'notify-send -u {urgency_map.get(urgency, "normal")} "{title}" "{message}"'
            os.system(cmd)

            for callback in self.callbacks:
                try:
                    callback({'type': 'notification', 'title': title, 'message': message})
                except:
                    pass

            return True
        except Exception as e:
            print(f"Linux 通知失败: {e}")
            return False

    def _notify_windows(self, title, message, urgency):
        """Windows 通知（使用 PowerShell）"""
        try:
            ps_command = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null

            $APP_ID = 'Python'

            $template = @"
            <toast>
                <visual>
                    <binding template="ToastText02">
                        <text id="1">{title}</text>
                        <text id="2">{message}</text>
                    </binding>
                </visual>
            </toast>
            "@

            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($APP_ID).Show($toast)
            '''

            import subprocess
            subprocess.run(['powershell', '-Command', ps_command], check=False)

            for callback in self.callbacks:
                try:
                    callback({'type': 'notification', 'title': title, 'message': message})
                except:
                    pass

            return True
        except Exception as e:
            print(f"Windows 通知失败: {e}")
            return False

    def play_sound(self, sound_type='default'):
        """播放提醒音"""
        try:
            if self.platform == 'darwin':
                # macOS: 使用内置声音
                sound_map = {
                    'default': 'Glass',
                    'bell': 'Ping',
                    'alarm': 'Alarm',
                    'beep': 'Beep'
                }
                sound = sound_map.get(sound_type, 'Glass')
                os.system(f"afplay /System/Library/Sounds/{sound}.aiff")
                return True
            elif self.platform == 'linux':
                # Linux: 使用 paplay
                os.system("paplay /usr/share/sounds/freedesktop/stereo/complete.oga")
                return True
            elif self.platform == 'win32':
                # Windows: 使用 winsound
                import winsound
                winsound.Beep(1000, 500)  # 频率1000Hz，持续500ms
                return True
        except Exception as e:
            print(f"⚠️ 播放声音失败: {e}")
            return False

    def create_popup_window(self, title, message, timeout=5):
        """创建弹窗（简单的控制台显示）"""
        try:
            border = "=" * 60
            print(f"\n{border}")
            print(f"🔔 {title}")
            print(f"{'-' * 60}")
            print(f"{message}")
            print(f"{border}\n")
            return True
        except Exception as e:
            print(f"❌ 弹窗创建失败: {e}")
            return False

    def toast_notification(self, title, message, timeout=5):
        """组合通知：系统通知 + 弹窗 + 声音"""
        try:
            # 1. 系统通知
            self.notify(title, message, urgency='normal')

            # 2. 播放声音
            self.play_sound('default')

            # 3. 弹窗显示
            self.create_popup_window(title, message, timeout)

            return True
        except Exception as e:
            print(f"❌ Toast通知失败: {e}")
            return False


class NotificationQueue:
    """通知队列管理器"""

    def __init__(self):
        self.notifications = []
        self.service = NotificationService()

    def enqueue(self, title, message, scheduled_time=None, user_id=None):
        """
        添加通知到队列

        Args:
            title: 通知标题
            message: 通知内容
            scheduled_time: 计划时间 (datetime对象或时间戳字符串)
            user_id: 用户ID

        Returns:
            dict: 通知对象
        """
        notification = {
            'id': len(self.notifications) + 1,
            'title': title,
            'message': message,
            'scheduled_time': scheduled_time,
            'user_id': user_id,
            'created_at': dt.now().isoformat(),
            'status': 'pending',  # pending, sent, dismissed
            'delivered_at': None
        }

        self.notifications.append(notification)
        return notification

    def get_pending_notifications(self):
        """获取待处理的通知"""
        now = dt.now()
        pending = []

        for notif in self.notifications:
            if notif['status'] == 'pending' and notif['scheduled_time']:
                scheduled = notif['scheduled_time']
                if isinstance(scheduled, str):
                    scheduled = dt.fromisoformat(scheduled)

                if scheduled <= now:
                    pending.append(notif)

        return pending

    def send_notification(self, notification_id):
        """发送指定的通知"""
        for notif in self.notifications:
            if notif['id'] == notification_id:
                self.service.toast_notification(
                    notif['title'],
                    notif['message']
                )
                notif['status'] = 'sent'
                notif['delivered_at'] = dt.now().isoformat()
                return True

        return False

    def dismiss_notification(self, notification_id):
        """关闭通知"""
        for notif in self.notifications:
            if notif['id'] == notification_id:
                notif['status'] = 'dismissed'
                return True
        return False

    def get_notification_history(self, user_id=None):
        """获取通知历史"""
        if user_id:
            return [n for n in self.notifications if n['user_id'] == user_id]
        return self.notifications


# 全局实例
_notification_service = None
_notification_queue = None

def get_notification_service():
    """获取全局通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service

def get_notification_queue():
    """获取全局通知队列实例"""
    global _notification_queue
    if _notification_queue is None:
        _notification_queue = NotificationQueue()
    return _notification_queue
