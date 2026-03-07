#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
留言板管理器
提供留言、回复、点赞等功能
支持便签墙功能：心情标签、背景颜色、图片、表情回应
"""

from datetime import datetime
import random

# 心情标签配置
MOOD_TAGS = {
    'happy': {'emoji': '😊', 'label': '开心', 'color': '#FFD54F'},
    'sad': {'emoji': '😢', 'label': '难过', 'color': '#90CAF9'},
    'excited': {'emoji': '🎉', 'label': '兴奋', 'color': '#FF8A80'},
    'calm': {'emoji': '😌', 'label': '平静', 'color': '#A5D6A7'},
    'thinking': {'emoji': '🤔', 'label': '思考', 'color': '#CE93D8'},
    'love': {'emoji': '❤️', 'label': '爱心', 'color': '#F48FB1'},
    'tired': {'emoji': '😴', 'label': '疲惫', 'color': '#BCAAA4'},
    'angry': {'emoji': '😠', 'label': '生气', 'color': '#EF5350'}
}

# 便签背景颜色预设
BG_COLORS = [
    '#FFF9C4',  # 黄色便签
    '#F8BBD0',  # 粉色便签
    '#B2DFDB',  # 青色便签
    '#C5E1A5',  # 绿色便签
    '#D1C4E9',  # 紫色便签
    '#FFCCBC',  # 橙色便签
    '#CFD8DC',  # 灰蓝色便签
    '#FFECB3',  # 浅黄色便签
]

# 表情回应类型
REACTION_TYPES = {
    'like': '👍',
    'love': '❤️',
    'haha': '😂',
    'wow': '😮',
    'sad': '😢',
    'angry': '😠'
}


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
            owner_id: 留言板主人ID（已废弃，保留兼容性）

        Returns:
            回复列表
        """
        try:
            # 在动态墙模式下，如果用户能看到父留言，就能看到所有回复
            # 不需要额外的权限检查
            sql = """
                SELECT gm.id, gm.author_id, u.username as author_username,
                       u.avatar_url as author_avatar, gm.content, gm.is_public,
                       gm.parent_id, gm.like_count, gm.created_at,
                       (SELECT COUNT(*) FROM likes WHERE target_type = 'guestbook_message'
                        AND target_id = gm.id AND user_id = %s) as is_liked
                FROM guestbook_messages gm
                JOIN users u ON gm.author_id = u.id
                WHERE gm.parent_id = %s
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

    def post_message_v2(self, owner_id, author_id, content,
                        mood_tag=None, bg_color='#FFF9C4',
                        image_id=None, image_ids=None, is_public=True, parent_id=None,
                        visibility='all_friends', visible_to_users=None):
        """发表留言（增强版 - 支持便签墙功能和可见范围控制）

        Args:
            owner_id: 留言板主人ID（发布者自己的ID）
            author_id: 留言者ID（发布者自己的ID）
            content: 留言内容
            mood_tag: 心情标签（happy/sad/excited等）
            bg_color: 背景颜色（默认黄色）
            image_id: 关联图片ID（单张，兼容旧版）
            image_ids: 关联图片ID列表（多张，新版）
            is_public: 是否公开（已废弃，使用visibility代替）
            parent_id: 父留言ID（回复时使用）
            visibility: 可见范围（all_friends=所有好友，specific_friends=指定好友，private=仅自己）
            visible_to_users: 可见用户ID列表（仅当visibility=specific_friends时有效）

        Returns:
            {'success': bool, 'message_id': int}
        """
        try:
            # 注意：新的逻辑是发布到自己的墙上，owner_id 和 author_id 应该相同
            # 如果不同，说明是给别人留言（保留旧逻辑兼容性）
            if owner_id != author_id:
                friendship_status = self.friendship_manager.check_friendship(author_id, owner_id)
                if friendship_status != 'accepted':
                    return {'success': False, 'message': '只能给好友留言'}

            # 生成随机位置和旋转角度（便签墙效果）
            position_x = random.uniform(0, 100)
            position_y = random.uniform(0, 100)
            rotation = random.uniform(-5, 5)

            # 处理可见用户列表
            import json
            visible_to_json = None
            if visibility == 'specific_friends' and visible_to_users:
                visible_to_json = json.dumps(visible_to_users)

            # 处理图片ID列表
            image_ids_json = None
            if image_ids:
                # 如果提供了 image_ids 列表
                image_ids_json = json.dumps(image_ids)
            elif image_id:
                # 如果只提供了单个 image_id（兼容旧版）
                image_ids_json = json.dumps([image_id])

            # 插入留言记录
            sql = """
                INSERT INTO guestbook_messages
                (owner_id, author_id, content, mood_tag, bg_color, image_id, image_ids,
                 position_x, position_y, rotation, is_public, parent_id,
                 visibility, visible_to_users)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.db.execute(sql, (owner_id, author_id, content, mood_tag, bg_color,
                                 image_id, image_ids_json, position_x, position_y, rotation,
                                 is_public, parent_id, visibility, visible_to_json))

            # 获取插入的留言ID
            message_id = self.db.query_one("SELECT LAST_INSERT_ID() as id")['id']

            return {'success': True, 'message_id': message_id}

        except Exception as e:
            print(f"发表留言失败: {e}")
            return {'success': False, 'message': f'发表失败: {str(e)}'}

    def get_messages_v2(self, owner_id, viewer_id, limit=50, offset=0):
        """获取留言列表（增强版 - 动态墙模式）

        查询逻辑：
        1. 我自己发布的所有内容
        2. 我的好友发布的内容，且：
           - visibility='all_friends' 的内容
           - visibility='specific_friends' 且 visible_to_users 包含我的ID

        Args:
            owner_id: 留言板主人ID（已废弃，保留兼容性）
            viewer_id: 查看者ID（当前用户ID）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            [{'id', 'author_id', 'author_username', 'author_avatar',
              'content', 'mood_tag', 'bg_color', 'image_id', 'image_path',
              'position_x', 'position_y', 'rotation', 'visibility',
              'reactions': {...}, 'replies': [...], 'created_at'}]
        """
        try:
            import json

            # 获取我的好友列表
            friends_sql = """
                SELECT friend_id
                FROM friendships
                WHERE user_id = %s AND status = 'accepted'
                UNION
                SELECT user_id as friend_id
                FROM friendships
                WHERE friend_id = %s AND status = 'accepted'
            """
            friends_result = self.db.query(friends_sql, (viewer_id, viewer_id))
            friend_ids = [f['friend_id'] for f in friends_result] if friends_result else []

            # 构建查询条件
            # 1. 我自己发布的
            # 2. 好友发布的且可见的
            if friend_ids:
                friend_ids_str = ','.join(map(str, friend_ids))
                visibility_condition = f"""
                    (gm.author_id = {viewer_id})
                    OR
                    (
                        gm.author_id IN ({friend_ids_str})
                        AND (
                            gm.visibility = 'all_friends'
                            OR (
                                gm.visibility = 'specific_friends'
                                AND JSON_CONTAINS(gm.visible_to_users, '{viewer_id}')
                            )
                        )
                    )
                """
            else:
                # 没有好友，只显示自己的
                visibility_condition = f"gm.author_id = {viewer_id}"

            # 查询留言（包含图片信息）
            sql = f"""
                SELECT gm.id, gm.author_id, u.username as author_username,
                       u.avatar_url as author_avatar, gm.content, gm.mood_tag,
                       gm.bg_color, gm.image_id, gm.image_ids, gm.position_x, gm.position_y,
                       gm.rotation, gm.is_public, gm.parent_id, gm.like_count,
                       gm.visibility, gm.visible_to_users, gm.created_at,
                       i.filename as image_filename, i.file_path as image_path,
                       (SELECT COUNT(*) FROM likes WHERE target_type = 'guestbook_message'
                        AND target_id = gm.id AND user_id = %s) as is_liked
                FROM guestbook_messages gm
                JOIN users u ON gm.author_id = u.id
                LEFT JOIN images i ON gm.image_id = i.id
                WHERE gm.parent_id IS NULL AND ({visibility_condition})
                ORDER BY gm.created_at DESC
                LIMIT %s OFFSET %s
            """
            results = self.db.query(sql, (viewer_id, limit, offset))

            # 转换datetime为字符串，添加表情回应和回复
            if results:
                for item in results:
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')

                    # 解析 visible_to_users JSON
                    if item.get('visible_to_users'):
                        try:
                            item['visible_to_users'] = json.loads(item['visible_to_users'])
                        except:
                            item['visible_to_users'] = []

                    # 解析 image_ids JSON 并获取所有图片信息
                    if item.get('image_ids'):
                        try:
                            image_ids_list = json.loads(item['image_ids'])
                            if image_ids_list:
                                # 查询所有图片的信息
                                image_ids_str = ','.join(map(str, image_ids_list))
                                images_sql = f"""
                                    SELECT id, filename, file_path
                                    FROM images
                                    WHERE id IN ({image_ids_str})
                                    ORDER BY FIELD(id, {image_ids_str})
                                """
                                images_result = self.db.query(images_sql)
                                item['images'] = images_result if images_result else []
                            else:
                                item['images'] = []
                        except Exception as e:
                            print(f"解析图片ID列表失败: {e}")
                            item['images'] = []
                    else:
                        # 兼容旧数据：如果没有 image_ids 但有 image_id，使用单张图片
                        if item.get('image_id') and item.get('image_path'):
                            item['images'] = [{
                                'id': item['image_id'],
                                'filename': item.get('image_filename'),
                                'file_path': item.get('image_path')
                            }]
                        else:
                            item['images'] = []

                    # 获取表情回应
                    item['reactions'] = self.get_message_reactions(item['id'])

                    # 获取回复
                    item['replies'] = self._get_replies(item['id'], viewer_id, owner_id)

            return results if results else []

        except Exception as e:
            print(f"获取留言列表失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def add_reaction(self, message_id, user_id, reaction_type):
        """添加表情回应

        Args:
            message_id: 留言ID
            user_id: 用户ID
            reaction_type: 表情类型（like/love/haha/wow/sad/angry）

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 验证表情类型
            if reaction_type not in REACTION_TYPES:
                return {'success': False, 'message': '无效的表情类型'}

            # 插入表情回应（如果已存在则更新时间）
            sql = """
                INSERT INTO guestbook_reactions (message_id, user_id, reaction_type)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE created_at = CURRENT_TIMESTAMP
            """
            self.db.execute(sql, (message_id, user_id, reaction_type))

            return {'success': True, 'message': '表情回应成功'}

        except Exception as e:
            print(f"添加表情回应失败: {e}")
            return {'success': False, 'message': f'操作失败: {str(e)}'}

    def remove_reaction(self, message_id, user_id, reaction_type):
        """移除表情回应

        Args:
            message_id: 留言ID
            user_id: 用户ID
            reaction_type: 表情类型

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            sql = """
                DELETE FROM guestbook_reactions
                WHERE message_id = %s AND user_id = %s AND reaction_type = %s
            """
            affected = self.db.execute(sql, (message_id, user_id, reaction_type))

            if affected == 0:
                return {'success': False, 'message': '未找到该表情回应'}

            return {'success': True, 'message': '移除表情回应成功'}

        except Exception as e:
            print(f"移除表情回应失败: {e}")
            return {'success': False, 'message': f'操作失败: {str(e)}'}

    def get_message_reactions(self, message_id):
        """获取留言的所有表情回应统计

        Args:
            message_id: 留言ID

        Returns:
            {'like': {'count': 3, 'users': ['张三', '李四']}, ...}
        """
        try:
            sql = """
                SELECT reaction_type, COUNT(*) as count,
                       GROUP_CONCAT(u.username SEPARATOR ',') as users
                FROM guestbook_reactions gr
                JOIN users u ON gr.user_id = u.id
                WHERE gr.message_id = %s
                GROUP BY reaction_type
            """
            results = self.db.query(sql, (message_id,))

            # 转换为字典格式
            reactions = {}
            if results:
                for row in results:
                    reactions[row['reaction_type']] = {
                        'count': row['count'],
                        'users': row['users'].split(',') if row['users'] else []
                    }

            return reactions

        except Exception as e:
            print(f"获取表情回应失败: {e}")
            return {}
