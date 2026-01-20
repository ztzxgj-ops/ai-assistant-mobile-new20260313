#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
留言板管理器
提供留言、回复、点赞等功能
"""

from datetime import datetime


class GuestbookManager:
    """留言板管理器"""

    def __init__(self, db_manager, friendship_manager):
        """初始化留言板管理器

        Args:
            db_manager: MySQLManager实例
            friendship_manager: FriendshipManager实例
        """
        self.db = db_manager
        self.friendship_manager = friendship_manager

    def post_message(self, owner_id, author_id, content, is_public=True, parent_id=None):
        """发表留言

        Args:
            owner_id: 留言板主人ID
            author_id: 留言者ID
            content: 留言内容
            is_public: 是否公开
            parent_id: 父留言ID（回复时使用）

        Returns:
            {'success': bool, 'message_id': int}
        """
        try:
            # 验证好友关系（只能给好友留言）
            if owner_id != author_id:  # 不是给自己留言
                friendship_status = self.friendship_manager.check_friendship(author_id, owner_id)
                if friendship_status != 'accepted':
                    return {'success': False, 'message': '只能给好友留言'}

            # 插入留言记录
            sql = """
                INSERT INTO guestbook_messages (owner_id, author_id, content, is_public, parent_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            self.db.execute(sql, (owner_id, author_id, content, is_public, parent_id))

            # 获取插入的留言ID
            message_id = self.db.query_one("SELECT LAST_INSERT_ID() as id")['id']

            return {'success': True, 'message_id': message_id}

        except Exception as e:
            print(f"发表留言失败: {e}")
            return {'success': False, 'message': f'发表失败: {str(e)}'}

    def get_messages(self, owner_id, viewer_id, limit=50, offset=0):
        """获取留言列表

        Args:
            owner_id: 留言板主人ID
            viewer_id: 查看者ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            [{'id', 'author_id', 'author_username', 'author_avatar',
              'content', 'is_public', 'parent_id', 'like_count',
              'replies': [...], 'created_at'}]
        """
        try:
            # 构建权限条件
            if viewer_id == owner_id:
                # 留言板主人可以看到所有留言
                permission_condition = "1=1"
            else:
                # 其他人只能看到公开留言和自己的留言
                permission_condition = f"(gm.is_public = 1 OR gm.author_id = {viewer_id})"

            # 查询留言（只查询顶级留言，不包括回复）
            sql = f"""
                SELECT gm.id, gm.author_id, u.username as author_username,
                       u.avatar_url as author_avatar, gm.content, gm.is_public,
                       gm.parent_id, gm.like_count, gm.created_at,
                       (SELECT COUNT(*) FROM likes WHERE target_type = 'guestbook_message'
                        AND target_id = gm.id AND user_id = %s) as is_liked
                FROM guestbook_messages gm
                JOIN users u ON gm.author_id = u.id
                WHERE gm.owner_id = %s AND gm.parent_id IS NULL AND {permission_condition}
                ORDER BY gm.created_at DESC
                LIMIT %s OFFSET %s
            """
            results = self.db.query(sql, (viewer_id, owner_id, limit, offset))

            # 转换datetime为字符串
            if results:
                for item in results:
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')

                    # 获取回复
                    item['replies'] = self._get_replies(item['id'], viewer_id, owner_id)

            return results if results else []

        except Exception as e:
            print(f"获取留言列表失败: {e}")
            return []

    def _get_replies(self, parent_id, viewer_id, owner_id):
        """获取留言的回复列表（内部方法）

        Args:
            parent_id: 父留言ID
            viewer_id: 查看者ID
            owner_id: 留言板主人ID

        Returns:
            回复列表
        """
        try:
            # 构建权限条件
            if viewer_id == owner_id:
                permission_condition = "1=1"
            else:
                permission_condition = f"(gm.is_public = 1 OR gm.author_id = {viewer_id})"

            sql = f"""
                SELECT gm.id, gm.author_id, u.username as author_username,
                       u.avatar_url as author_avatar, gm.content, gm.is_public,
                       gm.parent_id, gm.like_count, gm.created_at,
                       (SELECT COUNT(*) FROM likes WHERE target_type = 'guestbook_message'
                        AND target_id = gm.id AND user_id = %s) as is_liked
                FROM guestbook_messages gm
                JOIN users u ON gm.author_id = u.id
                WHERE gm.parent_id = %s AND {permission_condition}
                ORDER BY gm.created_at ASC
            """
            results = self.db.query(sql, (viewer_id, parent_id))

            # 转换datetime为字符串
            if results:
                for item in results:
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')

            return results if results else []

        except Exception as e:
            print(f"获取回复失败: {e}")
            return []

    def delete_message(self, user_id, message_id):
        """删除留言

        Args:
            user_id: 当前用户ID
            message_id: 留言ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 验证权限：留言板主人或留言作者可删除
            check_sql = """
                SELECT owner_id, author_id FROM guestbook_messages WHERE id = %s
            """
            message = self.db.query_one(check_sql, (message_id,))

            if not message:
                return {'success': False, 'message': '留言不存在'}

            if message['owner_id'] != user_id and message['author_id'] != user_id:
                return {'success': False, 'message': '无权限删除此留言'}

            # 删除留言（级联删除回复）
            delete_sql = "DELETE FROM guestbook_messages WHERE id = %s"
            self.db.execute(delete_sql, (message_id,))

            return {'success': True, 'message': '留言已删除'}

        except Exception as e:
            print(f"删除留言失败: {e}")
            return {'success': False, 'message': f'删除失败: {str(e)}'}

    def like_message(self, user_id, message_id):
        """点赞留言

        Args:
            user_id: 当前用户ID
            message_id: 留言ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 检查是否已点赞
            check_sql = """
                SELECT id FROM likes
                WHERE user_id = %s AND target_type = 'guestbook_message' AND target_id = %s
            """
            existing = self.db.query_one(check_sql, (user_id, message_id))

            if existing:
                return {'success': False, 'message': '已经点赞过了'}

            # 插入点赞记录
            insert_sql = """
                INSERT INTO likes (user_id, target_type, target_id)
                VALUES (%s, 'guestbook_message', %s)
            """
            self.db.execute(insert_sql, (user_id, message_id))

            # 更新点赞数
            update_sql = "UPDATE guestbook_messages SET like_count = like_count + 1 WHERE id = %s"
            self.db.execute(update_sql, (message_id,))

            return {'success': True, 'message': '点赞成功'}

        except Exception as e:
            print(f"点赞失败: {e}")
            return {'success': False, 'message': f'点赞失败: {str(e)}'}

    def unlike_message(self, user_id, message_id):
        """取消点赞

        Args:
            user_id: 当前用户ID
            message_id: 留言ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 删除点赞记录
            delete_sql = """
                DELETE FROM likes
                WHERE user_id = %s AND target_type = 'guestbook_message' AND target_id = %s
            """
            affected = self.db.execute(delete_sql, (user_id, message_id))

            if affected == 0:
                return {'success': False, 'message': '未点赞过'}

            # 更新点赞数
            update_sql = "UPDATE guestbook_messages SET like_count = like_count - 1 WHERE id = %s"
            self.db.execute(update_sql, (message_id,))

            return {'success': True, 'message': '取消点赞成功'}

        except Exception as e:
            print(f"取消点赞失败: {e}")
            return {'success': False, 'message': f'取消点赞失败: {str(e)}'}
