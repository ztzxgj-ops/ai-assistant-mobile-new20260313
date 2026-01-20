#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
好友关系管理器
提供用户搜索、好友请求、好友列表等功能
"""

from datetime import datetime


class FriendshipManager:
    """好友关系管理器"""

    def __init__(self, db_manager):
        """初始化好友管理器

        Args:
            db_manager: MySQLManager实例
        """
        self.db = db_manager

    def search_users(self, keyword, user_id=None, limit=20):
        """搜索用户（按用户名）

        Args:
            keyword: 搜索关键词
            user_id: 当前用户ID（排除自己）
            limit: 返回数量限制

        Returns:
            用户列表 [{'id', 'username', 'avatar_url', 'friendship_status'}]
        """
        try:
            # 构建查询SQL
            if user_id:
                sql = """
                    SELECT u.id, u.username, u.avatar_url,
                           COALESCE(f.status, 'none') as friendship_status,
                           CASE
                               WHEN f.user_id = %s THEN 'sent'
                               WHEN f.friend_id = %s THEN 'received'
                               ELSE 'none'
                           END as request_direction
                    FROM users u
                    LEFT JOIN friendships f ON
                        (f.user_id = %s AND f.friend_id = u.id) OR
                        (f.friend_id = %s AND f.user_id = u.id)
                    WHERE u.username LIKE %s AND u.id != %s
                    ORDER BY u.username
                    LIMIT %s
                """
                params = (user_id, user_id, user_id, user_id, f'%{keyword}%', user_id, limit)
            else:
                sql = """
                    SELECT id, username, avatar_url, 'none' as friendship_status, 'none' as request_direction
                    FROM users
                    WHERE username LIKE %s
                    ORDER BY username
                    LIMIT %s
                """
                params = (f'%{keyword}%', limit)

            results = self.db.query(sql, params)
            return results if results else []

        except Exception as e:
            print(f"搜索用户失败: {e}")
            return []

    def send_friend_request(self, user_id, friend_id):
        """发送好友请求

        Args:
            user_id: 发起用户ID
            friend_id: 目标用户ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 1. 检查是否是自己
            if user_id == friend_id:
                return {'success': False, 'message': '不能添加自己为好友'}

            # 2. 检查目标用户是否存在
            check_user_sql = "SELECT id FROM users WHERE id = %s"
            target_user = self.db.query_one(check_user_sql, (friend_id,))
            if not target_user:
                return {'success': False, 'message': '目标用户不存在'}

            # 3. 检查是否已经是好友或已发送请求
            check_sql = """
                SELECT id, status, user_id, friend_id
                FROM friendships
                WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)
            """
            existing = self.db.query_one(check_sql, (user_id, friend_id, friend_id, user_id))

            if existing:
                if existing['status'] == 'accepted':
                    return {'success': False, 'message': '你们已经是好友了'}
                elif existing['status'] == 'pending':
                    if existing['user_id'] == user_id:
                        return {'success': False, 'message': '已发送好友请求，请等待对方回应'}
                    else:
                        # 对方已经向我发送请求，直接接受
                        return self.accept_friend_request(user_id, existing['id'])
                elif existing['status'] == 'blocked':
                    return {'success': False, 'message': '无法添加该用户'}
                elif existing['status'] == 'rejected':
                    # 如果之前被拒绝，可以重新发送请求
                    update_sql = """
                        UPDATE friendships
                        SET status = 'pending', requested_at = NOW(), updated_at = NOW()
                        WHERE id = %s
                    """
                    self.db.execute(update_sql, (existing['id'],))
                    return {'success': True, 'message': '好友请求已重新发送'}

            # 4. 插入新的好友请求
            insert_sql = """
                INSERT INTO friendships (user_id, friend_id, status, requested_at)
                VALUES (%s, %s, 'pending', NOW())
            """
            self.db.execute(insert_sql, (user_id, friend_id))

            return {'success': True, 'message': '好友请求已发送'}

        except Exception as e:
            print(f"发送好友请求失败: {e}")
            return {'success': False, 'message': f'发送失败: {str(e)}'}

    def accept_friend_request(self, user_id, friendship_id):
        """接受好友请求

        Args:
            user_id: 当前用户ID（接收方）
            friendship_id: 好友关系ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 1. 验证权限：确保user_id是friend_id（接收方）
            check_sql = """
                SELECT user_id, friend_id, status
                FROM friendships
                WHERE id = %s
            """
            friendship = self.db.query_one(check_sql, (friendship_id,))

            if not friendship:
                return {'success': False, 'message': '好友请求不存在'}

            if friendship['friend_id'] != user_id:
                return {'success': False, 'message': '无权限操作此请求'}

            if friendship['status'] != 'pending':
                return {'success': False, 'message': '该请求已处理'}

            # 2. 更新状态为accepted
            update_sql = """
                UPDATE friendships
                SET status = 'accepted', accepted_at = NOW(), updated_at = NOW()
                WHERE id = %s
            """
            self.db.execute(update_sql, (friendship_id,))

            # 3. 创建反向关系（双向好友）
            reverse_sql = """
                INSERT INTO friendships (user_id, friend_id, status, requested_at, accepted_at)
                VALUES (%s, %s, 'accepted', NOW(), NOW())
                ON DUPLICATE KEY UPDATE status = 'accepted', accepted_at = NOW()
            """
            self.db.execute(reverse_sql, (friendship['friend_id'], friendship['user_id']))

            return {'success': True, 'message': '已成为好友'}

        except Exception as e:
            print(f"接受好友请求失败: {e}")
            return {'success': False, 'message': f'操作失败: {str(e)}'}

    def reject_friend_request(self, user_id, friendship_id):
        """拒绝好友请求

        Args:
            user_id: 当前用户ID（接收方）
            friendship_id: 好友关系ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 验证权限
            check_sql = """
                SELECT user_id, friend_id, status
                FROM friendships
                WHERE id = %s
            """
            friendship = self.db.query_one(check_sql, (friendship_id,))

            if not friendship:
                return {'success': False, 'message': '好友请求不存在'}

            if friendship['friend_id'] != user_id:
                return {'success': False, 'message': '无权限操作此请求'}

            if friendship['status'] != 'pending':
                return {'success': False, 'message': '该请求已处理'}

            # 更新状态为rejected
            update_sql = """
                UPDATE friendships
                SET status = 'rejected', updated_at = NOW()
                WHERE id = %s
            """
            self.db.execute(update_sql, (friendship_id,))

            return {'success': True, 'message': '已拒绝好友请求'}

        except Exception as e:
            print(f"拒绝好友请求失败: {e}")
            return {'success': False, 'message': f'操作失败: {str(e)}'}

    def get_friend_requests(self, user_id, status='pending'):
        """获取好友请求列表（收到的）

        Args:
            user_id: 当前用户ID
            status: 状态过滤（pending/accepted/rejected）

        Returns:
            [{'id', 'user_id', 'username', 'avatar_url', 'requested_at', 'status'}]
        """
        try:
            sql = """
                SELECT f.id, f.user_id, u.username, u.avatar_url,
                       f.requested_at, f.status
                FROM friendships f
                JOIN users u ON f.user_id = u.id
                WHERE f.friend_id = %s AND f.status = %s
                ORDER BY f.requested_at DESC
            """
            results = self.db.query(sql, (user_id, status))

            # 转换datetime为字符串
            if results:
                for item in results:
                    if item.get('requested_at'):
                        item['requested_at'] = item['requested_at'].strftime('%Y-%m-%d %H:%M:%S')

            return results if results else []

        except Exception as e:
            print(f"获取好友请求失败: {e}")
            return []

    def get_friends_list(self, user_id):
        """获取好友列表

        Args:
            user_id: 当前用户ID

        Returns:
            [{'id', 'username', 'avatar_url', 'accepted_at'}]
        """
        try:
            sql = """
                SELECT u.id, u.username, u.avatar_url, f.accepted_at
                FROM friendships f
                JOIN users u ON f.friend_id = u.id
                WHERE f.user_id = %s AND f.status = 'accepted'
                ORDER BY f.accepted_at DESC
            """
            results = self.db.query(sql, (user_id,))

            # 转换datetime为字符串
            if results:
                for item in results:
                    if item.get('accepted_at'):
                        item['accepted_at'] = item['accepted_at'].strftime('%Y-%m-%d %H:%M:%S')

            return results if results else []

        except Exception as e:
            print(f"获取好友列表失败: {e}")
            return []

    def delete_friend(self, user_id, friend_id):
        """删除好友（双向删除）

        Args:
            user_id: 当前用户ID
            friend_id: 好友ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 删除双向关系
            delete_sql = """
                DELETE FROM friendships
                WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)
            """
            affected = self.db.execute(delete_sql, (user_id, friend_id, friend_id, user_id))

            if affected > 0:
                return {'success': True, 'message': '已删除好友'}
            else:
                return {'success': False, 'message': '好友关系不存在'}

        except Exception as e:
            print(f"删除好友失败: {e}")
            return {'success': False, 'message': f'删除失败: {str(e)}'}

    def block_user(self, user_id, target_id):
        """拉黑用户

        Args:
            user_id: 当前用户ID
            target_id: 目标用户ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 检查是否已存在关系
            check_sql = """
                SELECT id FROM friendships
                WHERE user_id = %s AND friend_id = %s
            """
            existing = self.db.query_one(check_sql, (user_id, target_id))

            if existing:
                # 更新为blocked
                update_sql = """
                    UPDATE friendships
                    SET status = 'blocked', updated_at = NOW()
                    WHERE id = %s
                """
                self.db.execute(update_sql, (existing['id'],))
            else:
                # 创建新的blocked关系
                insert_sql = """
                    INSERT INTO friendships (user_id, friend_id, status, requested_at)
                    VALUES (%s, %s, 'blocked', NOW())
                """
                self.db.execute(insert_sql, (user_id, target_id))

            # 删除反向关系（如果存在）
            delete_sql = """
                DELETE FROM friendships
                WHERE user_id = %s AND friend_id = %s
            """
            self.db.execute(delete_sql, (target_id, user_id))

            return {'success': True, 'message': '已拉黑该用户'}

        except Exception as e:
            print(f"拉黑用户失败: {e}")
            return {'success': False, 'message': f'操作失败: {str(e)}'}

    def check_friendship(self, user_id, target_id):
        """检查好友关系状态

        Args:
            user_id: 当前用户ID
            target_id: 目标用户ID

        Returns:
            'none' | 'pending_sent' | 'pending_received' | 'accepted' | 'blocked' | 'rejected'
        """
        try:
            sql = """
                SELECT status, user_id, friend_id
                FROM friendships
                WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)
            """
            result = self.db.query_one(sql, (user_id, target_id, target_id, user_id))

            if not result:
                return 'none'

            if result['status'] == 'accepted':
                return 'accepted'
            elif result['status'] == 'blocked':
                return 'blocked'
            elif result['status'] == 'rejected':
                return 'rejected'
            elif result['status'] == 'pending':
                if result['user_id'] == user_id:
                    return 'pending_sent'
                else:
                    return 'pending_received'

            return 'none'

        except Exception as e:
            print(f"检查好友关系失败: {e}")
            return 'none'

    def get_sent_requests(self, user_id):
        """获取已发送的好友请求列表

        Args:
            user_id: 当前用户ID

        Returns:
            [{'id', 'friend_id', 'username', 'avatar_url', 'requested_at', 'status'}]
        """
        try:
            sql = """
                SELECT f.id, f.friend_id, u.username, u.avatar_url,
                       f.requested_at, f.status
                FROM friendships f
                JOIN users u ON f.friend_id = u.id
                WHERE f.user_id = %s AND f.status = 'pending'
                ORDER BY f.requested_at DESC
            """
            results = self.db.query(sql, (user_id,))

            # 转换datetime为字符串
            if results:
                for item in results:
                    if item.get('requested_at'):
                        item['requested_at'] = item['requested_at'].strftime('%Y-%m-%d %H:%M:%S')

            return results if results else []

        except Exception as e:
            print(f"获取已发送请求失败: {e}")
            return []
