#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容分享管理器
提供内容发布、查看、点赞等功能
"""

import json
from datetime import datetime


class SharedContentManager:
    """内容分享管理器"""

    def __init__(self, db_manager, friendship_manager):
        """初始化内容分享管理器

        Args:
            db_manager: MySQLManager实例
            friendship_manager: FriendshipManager实例
        """
        self.db = db_manager
        self.friendship_manager = friendship_manager

    def create_share(self, user_id, content_type, title=None, content=None,
                     image_id=None, visibility='friends', tags=None):
        """创建分享

        Args:
            user_id: 分享者ID
            content_type: 内容类型（text/image/note）
            title: 标题
            content: 文字内容
            image_id: 图片ID
            visibility: 可见性（public/friends/private）
            tags: 标签列表

        Returns:
            {'success': bool, 'share_id': int}
        """
        try:
            # 转换tags为JSON字符串
            tags_json = json.dumps(tags) if tags else None

            sql = """
                INSERT INTO shared_contents (user_id, content_type, title, content,
                                            image_id, visibility, tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.db.execute(sql, (user_id, content_type, title, content,
                                 image_id, visibility, tags_json))

            # 获取插入的分享ID
            share_id = self.db.query_one("SELECT LAST_INSERT_ID() as id")['id']

            return {'success': True, 'share_id': share_id}

        except Exception as e:
            print(f"创建分享失败: {e}")
            return {'success': False, 'message': f'创建失败: {str(e)}'}

    def get_share_list(self, user_id, visibility_filter=None, limit=20, offset=0):
        """获取分享列表（好友动态）

        Args:
            user_id: 当前用户ID
            visibility_filter: 可见性过滤（None=所有可见的）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            [{'id', 'user_id', 'username', 'avatar_url', 'content_type',
              'title', 'content', 'image_info', 'tags', 'view_count',
              'like_count', 'is_liked', 'created_at'}]
        """
        try:
            # 获取好友列表
            friends = self.friendship_manager.get_friends_list(user_id)
            friend_ids = [f['id'] for f in friends]
            friend_ids.append(user_id)  # 包含自己

            # 构建查询条件
            if friend_ids:
                friend_ids_str = ','.join(map(str, friend_ids))
                visibility_condition = f"""
                    (sc.visibility = 'public')
                    OR (sc.visibility = 'friends' AND sc.user_id IN ({friend_ids_str}))
                    OR (sc.user_id = {user_id})
                """
            else:
                visibility_condition = f"(sc.visibility = 'public' OR sc.user_id = {user_id})"

            # 查询分享列表
            sql = f"""
                SELECT sc.id, sc.user_id, u.username, u.avatar_url,
                       sc.content_type, sc.title, sc.content, sc.image_id,
                       sc.tags, sc.view_count, sc.like_count, sc.created_at,
                       img.filename as image_filename, img.file_path as image_path,
                       (SELECT COUNT(*) FROM likes WHERE target_type = 'shared_content'
                        AND target_id = sc.id AND user_id = %s) as is_liked
                FROM shared_contents sc
                JOIN users u ON sc.user_id = u.id
                LEFT JOIN images img ON sc.image_id = img.id
                WHERE {visibility_condition}
                ORDER BY sc.created_at DESC
                LIMIT %s OFFSET %s
            """
            results = self.db.query(sql, (user_id, limit, offset))

            # 转换datetime为字符串，整理数据
            if results:
                for item in results:
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')

                    # 解析tags
                    if item.get('tags'):
                        try:
                            item['tags'] = json.loads(item['tags'])
                        except:
                            item['tags'] = []
                    else:
                        item['tags'] = []

                    # 整理图片信息
                    if item.get('image_id'):
                        item['image_info'] = {
                            'id': item['image_id'],
                            'filename': item.get('image_filename'),
                            'path': item.get('image_path')
                        }
                    else:
                        item['image_info'] = None

                    # 删除临时字段
                    item.pop('image_filename', None)
                    item.pop('image_path', None)

            return results if results else []

        except Exception as e:
            print(f"获取分享列表失败: {e}")
            return []

    def get_user_shares(self, user_id, target_user_id, limit=20, offset=0):
        """获取某用户的分享列表

        Args:
            user_id: 当前用户ID
            target_user_id: 目标用户ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            分享列表
        """
        try:
            # 检查权限
            is_friend = self.friendship_manager.check_friendship(user_id, target_user_id) == 'accepted'
            is_self = (user_id == target_user_id)

            # 构建可见性条件
            if is_self:
                visibility_condition = "1=1"  # 自己可以看到所有
            elif is_friend:
                visibility_condition = "sc.visibility IN ('public', 'friends')"
            else:
                visibility_condition = "sc.visibility = 'public'"

            sql = f"""
                SELECT sc.id, sc.user_id, u.username, u.avatar_url,
                       sc.content_type, sc.title, sc.content, sc.image_id,
                       sc.tags, sc.view_count, sc.like_count, sc.created_at,
                       img.filename as image_filename, img.file_path as image_path,
                       (SELECT COUNT(*) FROM likes WHERE target_type = 'shared_content'
                        AND target_id = sc.id AND user_id = %s) as is_liked
                FROM shared_contents sc
                JOIN users u ON sc.user_id = u.id
                LEFT JOIN images img ON sc.image_id = img.id
                WHERE sc.user_id = %s AND {visibility_condition}
                ORDER BY sc.created_at DESC
                LIMIT %s OFFSET %s
            """
            results = self.db.query(sql, (user_id, target_user_id, limit, offset))

            # 转换datetime为字符串，整理数据
            if results:
                for item in results:
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')

                    # 解析tags
                    if item.get('tags'):
                        try:
                            item['tags'] = json.loads(item['tags'])
                        except:
                            item['tags'] = []
                    else:
                        item['tags'] = []

                    # 整理图片信息
                    if item.get('image_id'):
                        item['image_info'] = {
                            'id': item['image_id'],
                            'filename': item.get('image_filename'),
                            'path': item.get('image_path')
                        }
                    else:
                        item['image_info'] = None

                    item.pop('image_filename', None)
                    item.pop('image_path', None)

            return results if results else []

        except Exception as e:
            print(f"获取用户分享失败: {e}")
            return []

    def delete_share(self, user_id, share_id):
        """删除分享（仅作者可删除）

        Args:
            user_id: 当前用户ID
            share_id: 分享ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 验证权限
            check_sql = "SELECT user_id FROM shared_contents WHERE id = %s"
            share = self.db.query_one(check_sql, (share_id,))

            if not share:
                return {'success': False, 'message': '分享不存在'}

            if share['user_id'] != user_id:
                return {'success': False, 'message': '只能删除自己的分享'}

            # 删除分享
            delete_sql = "DELETE FROM shared_contents WHERE id = %s"
            self.db.execute(delete_sql, (share_id,))

            return {'success': True, 'message': '分享已删除'}

        except Exception as e:
            print(f"删除分享失败: {e}")
            return {'success': False, 'message': f'删除失败: {str(e)}'}

    def increment_view_count(self, share_id):
        """增加浏览次数

        Args:
            share_id: 分享ID

        Returns:
            {'success': bool}
        """
        try:
            sql = "UPDATE shared_contents SET view_count = view_count + 1 WHERE id = %s"
            self.db.execute(sql, (share_id,))
            return {'success': True}

        except Exception as e:
            print(f"增加浏览次数失败: {e}")
            return {'success': False}

    def like_share(self, user_id, share_id):
        """点赞分享

        Args:
            user_id: 当前用户ID
            share_id: 分享ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 检查是否已点赞
            check_sql = """
                SELECT id FROM likes
                WHERE user_id = %s AND target_type = 'shared_content' AND target_id = %s
            """
            existing = self.db.query_one(check_sql, (user_id, share_id))

            if existing:
                return {'success': False, 'message': '已经点赞过了'}

            # 插入点赞记录
            insert_sql = """
                INSERT INTO likes (user_id, target_type, target_id)
                VALUES (%s, 'shared_content', %s)
            """
            self.db.execute(insert_sql, (user_id, share_id))

            # 更新点赞数
            update_sql = "UPDATE shared_contents SET like_count = like_count + 1 WHERE id = %s"
            self.db.execute(update_sql, (share_id,))

            return {'success': True, 'message': '点赞成功'}

        except Exception as e:
            print(f"点赞失败: {e}")
            return {'success': False, 'message': f'点赞失败: {str(e)}'}

    def unlike_share(self, user_id, share_id):
        """取消点赞

        Args:
            user_id: 当前用户ID
            share_id: 分享ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 删除点赞记录
            delete_sql = """
                DELETE FROM likes
                WHERE user_id = %s AND target_type = 'shared_content' AND target_id = %s
            """
            affected = self.db.execute(delete_sql, (user_id, share_id))

            if affected == 0:
                return {'success': False, 'message': '未点赞过'}

            # 更新点赞数
            update_sql = "UPDATE shared_contents SET like_count = like_count - 1 WHERE id = %s"
            self.db.execute(update_sql, (share_id,))

            return {'success': True, 'message': '取消点赞成功'}

        except Exception as e:
            print(f"取消点赞失败: {e}")
            return {'success': False, 'message': f'取消点赞失败: {str(e)}'}
