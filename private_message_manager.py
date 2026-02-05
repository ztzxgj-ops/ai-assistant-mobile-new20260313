#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
私信消息管理器
提供一对一聊天、消息已读状态管理等功能
"""

from datetime import datetime
import sys


class PrivateMessageManager:
    """私信消息管理器"""

    def __init__(self, db_manager, friendship_manager):
        """初始化私信管理器

        Args:
            db_manager: MySQLManager实例
            friendship_manager: FriendshipManager实例
        """
        self.db = db_manager
        self.friendship_manager = friendship_manager

    def send_message(self, sender_id, receiver_id, content, message_type='text', image_id=None, file_id=None):
        """发送私信

        Args:
            sender_id: 发送者ID
            receiver_id: 接收者ID
            content: 消息内容
            message_type: 消息类型（text/image/file）
            image_id: 图片ID（可选）
            file_id: 文件ID（可选）

        Returns:
            {'success': bool, 'message_id': int}
        """
        try:
            # 1. 验证好友关系（只能给好友发消息）
            friendship_status = self.friendship_manager.check_friendship(sender_id, receiver_id)
            if friendship_status != 'accepted':
                return {'success': False, 'message': '只能给好友发送消息'}

            # 2. 插入消息记录
            sql = """
                INSERT INTO private_messages (sender_id, receiver_id, content, message_type, image_id, file_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            self.db.execute(sql, (sender_id, receiver_id, content, message_type, image_id, file_id))

            # 获取插入的消息ID
            message_id = self.db.query_one("SELECT LAST_INSERT_ID() as id")['id']

            # 3. 发送WebSocket通知给接收者
            try:
                from websocket_server import get_websocket_server
                ws_server = get_websocket_server()

                # 获取发送者信息
                sender_info = self.db.query_one(
                    "SELECT id, username FROM users WHERE id = %s",
                    (sender_id,)
                )
                sender_name = sender_info['username'] if sender_info else '好友'

                # 准备消息数据
                message_data = {
                    'sender_id': sender_id,
                    'sender_name': sender_name,
                    'content': content[:100],  # 只发送前100个字符
                    'message_type': message_type,
                    'message_id': message_id
                }

                # 发送通知
                ws_server.send_message(receiver_id, message_data)
                print(f"✅ 已发送WebSocket通知给用户 {receiver_id}")
            except Exception as ws_e:
                print(f"⚠️ WebSocket通知发送失败: {ws_e}")
                # 不影响消息发送，继续返回成功

            return {'success': True, 'message_id': message_id}

        except Exception as e:
            print(f"发送私信失败: {e}")
            return {'success': False, 'message': f'发送失败: {str(e)}'}

    def get_conversation(self, user_id, friend_id, limit=50, offset=0):
        """获取与某人的聊天记录

        Args:
            user_id: 当前用户ID
            friend_id: 好友ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            [{'id', 'sender_id', 'receiver_id', 'sender_avatar_url', 'receiver_avatar_url',
              'content', 'message_type', 'is_read', 'created_at', 'image_info'}]
        """
        try:
            # 查询双向消息，包含发送者和接收者的头像
            sql = """
                SELECT pm.id, pm.sender_id, pm.receiver_id, pm.content,
                       pm.message_type, pm.image_id, pm.file_id, pm.is_read, pm.created_at,
                       sender.avatar_url as sender_avatar_url,
                       receiver.avatar_url as receiver_avatar_url,
                       img.filename as image_filename, img.file_path as image_path,
                       f.original_name as file_name, f.file_path as file_path_full
                FROM private_messages pm
                LEFT JOIN users sender ON pm.sender_id = sender.id
                LEFT JOIN users receiver ON pm.receiver_id = receiver.id
                LEFT JOIN images img ON pm.image_id = img.id
                LEFT JOIN files f ON pm.file_id = f.id
                WHERE (pm.sender_id = %s AND pm.receiver_id = %s)
                   OR (pm.sender_id = %s AND pm.receiver_id = %s)
                ORDER BY pm.created_at ASC
                LIMIT %s OFFSET %s
            """
            results = self.db.query(sql, (user_id, friend_id, friend_id, user_id, limit, offset))

            # 转换datetime为字符串，整理图片和文件信息
            if results:
                for item in results:
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')

                    # 整理图片信息
                    if item.get('image_id'):
                        item['image_info'] = {
                            'id': item['image_id'],
                            'filename': item.get('image_filename'),
                            'path': item.get('image_path')
                        }
                    # 整理文件信息
                    elif item.get('file_id'):
                        item['image_info'] = {  # 使用image_info保持兼容性
                            'id': item['file_id'],
                            'filename': item.get('file_name'),
                            'path': item.get('file_path_full')
                        }
                    else:
                        item['image_info'] = None

                    # 删除临时字段
                    item.pop('image_filename', None)
                    item.pop('image_path', None)
                    item.pop('file_name', None)
                    item.pop('file_path_full', None)

            return results if results else []

        except Exception as e:
            print(f"获取聊天记录失败: {e}")
            return []

    def get_conversation_list(self, user_id):
        """获取会话列表（最近联系人）

        Args:
            user_id: 当前用户ID

        Returns:
            [{'friend_id', 'friend_username', 'friend_avatar',
              'last_message', 'last_message_time', 'unread_count'}]
        """
        try:
            # 使用更简单的查询：先获取所有相关消息，然后在Python中处理
            sql = """
                SELECT
                    pm.id,
                    pm.sender_id,
                    pm.receiver_id,
                    pm.content,
                    pm.created_at,
                    pm.is_read
                FROM private_messages pm
                WHERE pm.sender_id = %s OR pm.receiver_id = %s
                ORDER BY pm.created_at DESC
            """
            messages = self.db.query(sql, (user_id, user_id))

            print(f"🔍 [get_conversation_list] user_id={user_id}, 查询到消息数量: {len(messages) if messages else 0}", flush=True)
            sys.stdout.flush()

            if not messages:
                return []

            # 在Python中按好友ID分组
            conversations = {}
            for msg in messages:
                # 确定对方ID
                friend_id = msg['receiver_id'] if msg['sender_id'] == user_id else msg['sender_id']

                if friend_id not in conversations:
                    conversations[friend_id] = {
                        'friend_id': friend_id,
                        'last_message': msg['content'],
                        'last_message_time': msg['created_at'],
                        'unread_count': 0
                    }

                # 统计未读消息（只统计对方发给我的未读消息）
                if msg['receiver_id'] == user_id and msg['is_read'] == 0:
                    conversations[friend_id]['unread_count'] += 1

            print(f"🔍 [get_conversation_list] 分组后会话数量: {len(conversations)}", flush=True)
            sys.stdout.flush()

            # 获取好友信息
            if conversations:
                friend_ids = list(conversations.keys())
                placeholders = ','.join(['%s'] * len(friend_ids))
                user_sql = f"""
                    SELECT id, username, avatar_url
                    FROM users
                    WHERE id IN ({placeholders})
                """
                users = self.db.query(user_sql, friend_ids)

                print(f"🔍 [get_conversation_list] 查询到用户信息数量: {len(users) if users else 0}", flush=True)
                sys.stdout.flush()

                # 将用户信息添加到会话中
                for user in users:
                    friend_id = user['id']
                    if friend_id in conversations:
                        conversations[friend_id]['friend_username'] = user['username']
                        conversations[friend_id]['friend_avatar'] = user['avatar_url']

            # 转换为列表并排序
            result = list(conversations.values())
            result.sort(key=lambda x: x['last_message_time'], reverse=True)

            # 转换datetime为字符串
            for item in result:
                if item.get('last_message_time'):
                    item['last_message_time'] = item['last_message_time'].strftime('%Y-%m-%d %H:%M:%S')
                print(f"  - friend_id={item.get('friend_id')}, username={item.get('friend_username')}, unread={item.get('unread_count')}", flush=True)
            sys.stdout.flush()

            return result

        except Exception as e:
            print(f"❌ 获取会话列表失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def mark_as_read(self, user_id, message_ids):
        """标记消息为已读

        Args:
            user_id: 当前用户ID（接收方）
            message_ids: 消息ID列表

        Returns:
            {'success': bool, 'count': int}
        """
        try:
            if not message_ids:
                return {'success': True, 'count': 0}

            # 构建IN子句
            placeholders = ','.join(['%s'] * len(message_ids))
            sql = f"""
                UPDATE private_messages
                SET is_read = 1, read_at = NOW()
                WHERE id IN ({placeholders}) AND receiver_id = %s AND is_read = 0
            """

            params = list(message_ids) + [user_id]
            affected = self.db.execute(sql, params)

            return {'success': True, 'count': affected}

        except Exception as e:
            print(f"标记已读失败: {e}")
            return {'success': False, 'message': f'操作失败: {str(e)}'}

    def get_unread_count(self, user_id):
        """获取未读消息总数

        Args:
            user_id: 当前用户ID

        Returns:
            int: 未读消息数
        """
        try:
            sql = """
                SELECT COUNT(*) as count
                FROM private_messages
                WHERE receiver_id = %s AND is_read = 0
            """
            result = self.db.query_one(sql, (user_id,))
            return result['count'] if result else 0

        except Exception as e:
            print(f"获取未读数失败: {e}")
            return 0

    def delete_message(self, user_id, message_id):
        """删除消息（仅发送者可删除）

        Args:
            user_id: 当前用户ID
            message_id: 消息ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 验证权限：只有发送者可以删除
            check_sql = """
                SELECT sender_id FROM private_messages WHERE id = %s
            """
            message = self.db.query_one(check_sql, (message_id,))

            if not message:
                return {'success': False, 'message': '消息不存在'}

            if message['sender_id'] != user_id:
                return {'success': False, 'message': '只能删除自己发送的消息'}

            # 删除消息
            delete_sql = "DELETE FROM private_messages WHERE id = %s"
            self.db.execute(delete_sql, (message_id,))

            return {'success': True, 'message': '消息已删除'}

        except Exception as e:
            print(f"删除消息失败: {e}")
            return {'success': False, 'message': f'删除失败: {str(e)}'}

    def delete_conversation(self, user_id, friend_id):
        """删除整个会话（双向删除）

        Args:
            user_id: 当前用户ID
            friend_id: 好友ID

        Returns:
            {'success': bool, 'message': str, 'count': int}
        """
        try:
            # 删除双向消息
            sql = """
                DELETE FROM private_messages
                WHERE (sender_id = %s AND receiver_id = %s)
                   OR (sender_id = %s AND receiver_id = %s)
            """
            affected = self.db.execute(sql, (user_id, friend_id, friend_id, user_id))

            return {'success': True, 'message': '会话已删除', 'count': affected}

        except Exception as e:
            print(f"删除会话失败: {e}")
            return {'success': False, 'message': f'删除失败: {str(e)}'}
