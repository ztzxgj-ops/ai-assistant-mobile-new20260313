#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Firebase Cloud Messaging 推送通知服务"""

import firebase_admin
from firebase_admin import credentials, messaging
import json
import os
from datetime import datetime

class FCMPushService:
    """FCM推送通知服务"""

    def __init__(self, config_path='firebase_config.json'):
        """
        初始化FCM服务

        Args:
            config_path: Firebase Admin SDK配置文件路径
        """
        self.initialized = False
        self.config_path = config_path

        # 尝试初始化Firebase
        if os.path.exists(config_path):
            try:
                cred = credentials.Certificate(config_path)
                firebase_admin.initialize_app(cred)
                self.initialized = True
                print(f"✅ FCM服务已初始化")
            except Exception as e:
                print(f"⚠️ FCM初始化失败: {e}")
                print(f"⚠️ 请确保 {config_path} 文件存在且格式正确")
        else:
            print(f"⚠️ FCM配置文件不存在: {config_path}")
            print(f"⚠️ 请从Firebase控制台下载服务账号JSON文件")

    def send_notification(self, device_token, title, body, data=None):
        """
        发送推送通知到单个设备

        Args:
            device_token: 设备FCM token
            title: 通知标题
            body: 通知内容
            data: 附加数据（可选）

        Returns:
            dict: 发送结果 {'success': bool, 'message': str}
        """
        if not self.initialized:
            return {
                'success': False,
                'message': 'FCM服务未初始化'
            }

        try:
            # 构建通知消息
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=device_token,
                # iOS特定配置
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1,
                            content_available=True,
                        )
                    )
                ),
                # Android特定配置
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='default',
                        priority='high',
                    )
                )
            )

            # 发送消息
            response = messaging.send(message)

            print(f"✅ 推送通知已发送: {response}")
            return {
                'success': True,
                'message': f'消息已发送: {response}'
            }

        except Exception as e:
            print(f"❌ 发送推送通知失败: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def send_multicast(self, device_tokens, title, body, data=None):
        """
        发送推送通知到多个设备

        Args:
            device_tokens: 设备FCM token列表
            title: 通知标题
            body: 通知内容
            data: 附加数据（可选）

        Returns:
            dict: 发送结果 {'success_count': int, 'failure_count': int, 'responses': list}
        """
        if not self.initialized:
            return {
                'success_count': 0,
                'failure_count': len(device_tokens),
                'message': 'FCM服务未初始化'
            }

        try:
            # 构建多播消息
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                tokens=device_tokens,
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1,
                            content_available=True,
                        )
                    )
                ),
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='default',
                        priority='high',
                    )
                )
            )

            # 发送消息
            response = messaging.send_multicast(message)

            print(f"✅ 多播推送已发送: 成功{response.success_count}个, 失败{response.failure_count}个")

            return {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'responses': [
                    {
                        'success': resp.success,
                        'message_id': resp.message_id if resp.success else None,
                        'error': str(resp.exception) if not resp.success else None
                    }
                    for resp in response.responses
                ]
            }

        except Exception as e:
            print(f"❌ 发送多播推送失败: {e}")
            return {
                'success_count': 0,
                'failure_count': len(device_tokens),
                'message': str(e)
            }

    def send_reminder_notification(self, device_tokens, reminder_content, reminder_id=None):
        """
        发送提醒通知（便捷方法）

        Args:
            device_tokens: 设备token（单个字符串或列表）
            reminder_content: 提醒内容
            reminder_id: 提醒ID（可选）

        Returns:
            dict: 发送结果
        """
        title = "📢 任务提醒"
        body = reminder_content
        data = {
            'type': 'reminder',
            'reminder_id': str(reminder_id) if reminder_id else '',
            'timestamp': datetime.now().isoformat()
        }

        # 判断是单个设备还是多个设备
        if isinstance(device_tokens, str):
            return self.send_notification(device_tokens, title, body, data)
        elif isinstance(device_tokens, list) and len(device_tokens) > 0:
            if len(device_tokens) == 1:
                return self.send_notification(device_tokens[0], title, body, data)
            else:
                return self.send_multicast(device_tokens, title, body, data)
        else:
            return {
                'success': False,
                'message': '没有有效的设备token'
            }


# 全局实例
_fcm_service = None

def get_fcm_service(config_path='firebase_config.json'):
    """获取全局FCM服务实例"""
    global _fcm_service
    if _fcm_service is None:
        _fcm_service = FCMPushService(config_path)
    return _fcm_service
