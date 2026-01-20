#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
私信消息管理器
提供一对一聊天、消息已读状态管理等功能
"""

from datetime import datetime


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
            # 查询所有与user_id相关的消息，按对方ID分组
            sql = """
                SELECT
                    CASE
                        WHEN pm.sender_id = %s THEN pm.receiver_id
                        ELSE pm.sender_id
                    END as friend_id,
                    u.username as friend_username,
                    u.avatar_url as friend_avatar,
                    (SELECT content FROM private_messages
                     WHERE (sender_id = %s AND receiver_id = friend_id)
                        OR (sender_id = friend_id AND receiver_id = %s)
                     ORDER BY created_at DESC LIMIT 1) as last_message,
                    MAX(pm.created_at) as last_message_time,
                    SUM(CASE WHEN pm.receiver_id = %s AND pm.is_read = 0 THEN 1 ELSE 0 END) as unread_count
                FROM private_messages pm
                JOIN users u ON u.id = CASE
                    WHEN pm.sender_id = %s THEN pm.receiver_id
                    ELSE pm.sender_id
                END
                WHERE pm.sender_id = %s OR pm.receiver_id = %s
                GROUP BY friend_id, u.username, u.avatar_url
                ORDER BY last_message_time DESC
            """
            results = self.db.query(sql, (user_id, user_id, user_id, user_id, user_id, user_id, user_id))

            # 添加调试日志
            print(f"🔍 [get_conversation_list] user_id={user_id}, 查询结果数量: {len(results) if results else 0}")
            if results:
                for item in results:
                    print(f"  - friend_id={item.get('friend_id')}, friend_username={item.get('friend_username')}, friend_avatar={item.get('friend_avatar')}")

            # 转换datetime为字符串
            if results:
                for item in results:
                    if item.get('last_message_time'):
                        item['last_message_time'] = item['last_message_time'].strftime('%Y-%m-%d %H:%M:%S')

            return results if results else []

        except Exception as e:
            print(f"获取会话列表失败: {e}")
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
