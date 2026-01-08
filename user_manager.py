#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用户管理模块 - MySQL版本"""

import hashlib
import secrets
from datetime import datetime, timedelta
from mysql_manager import MySQLManager


class UserManager:
    """基于MySQL的用户管理器"""

    def __init__(self, db_manager):
        """
        初始化用户管理器

        参数:
            db_manager: MySQLManager实例，用于数据库操作
        """
        if not isinstance(db_manager, MySQLManager):
            raise ValueError("db_manager must be an instance of MySQLManager")

        self.db = db_manager
        print("✅ 使用MySQL用户管理器")

    def hash_password(self, password):
        """密码哈希 - SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def generate_token(self):
        """生成随机token - 32字节安全随机数"""
        return secrets.token_urlsafe(32)

    def register(self, username, password, phone=''):
        """
        注册新用户

        参数:
            username: 用户名
            password: 密码（明文，将被哈希）
            phone: 电话号码（可选）

        返回:
            字典，包含success和message字段
        """
        # 检查用户名是否已存在
        existing_user = self.get_user_by_username(username)
        if existing_user:
            return {'success': False, 'message': '用户名已存在'}

        try:
            # 插入新用户
            sql = """
                INSERT INTO users (username, password_hash, phone, created_at)
                VALUES (%s, %s, %s, %s)
            """
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            user_id = self.db.execute(sql, (
                username,
                self.hash_password(password),
                phone,
                now
            ))

            return {
                'success': True,
                'message': '注册成功',
                'user_id': user_id
            }
        except Exception as e:
            return {'success': False, 'message': f'注册失败: {str(e)}'}

    def login(self, username, password):
        """
        用户登录

        参数:
            username: 用户名
            password: 密码（明文）

        返回:
            字典，包含success、message、token等字段
        """
        # 查询用户
        user = self.get_user_by_username(username)
        if not user:
            return {'success': False, 'message': '用户不存在'}

        # 验证密码
        if user['password_hash'] != self.hash_password(password):
            return {'success': False, 'message': '密码错误'}

        try:
            # 更新最后登录时间
            update_sql = "UPDATE users SET last_login = %s WHERE id = %s"
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db.execute(update_sql, (now, user['id']))

            # 生成token并创建会话
            token = self.generate_token()
            insert_sql = """
                INSERT INTO user_sessions (user_id, session_token, expires_at, created_at)
                VALUES (%s, %s, %s, %s)
            """
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            expires_at = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

            self.db.execute(insert_sql, (
                user['id'],
                token,
                expires_at,
                created_at
            ))

            return {
                'success': True,
                'message': '登录成功',
                'token': token,
                'user_id': user['id'],
                'username': user['username']
            }
        except Exception as e:
            return {'success': False, 'message': f'登录失败: {str(e)}'}

    def verify_token(self, token):
        """
        验证token并返回user_id

        参数:
            token: 会话token

        返回:
            字典，包含success、user_id等字段；如果token无效或过期，返回失败信息
        """
        try:
            # 查询会话
            sql = """
                SELECT id, user_id, expires_at
                FROM user_sessions
                WHERE session_token = %s
            """
            result = self.db.query_one(sql, (token,))

            if not result:
                return {'success': False, 'message': 'Token不存在'}

            # 检查是否过期
            expires_at = result['expires_at']
            if isinstance(expires_at, str):
                expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')

            if datetime.now() > expires_at:
                # 删除过期会话
                delete_sql = "DELETE FROM user_sessions WHERE session_token = %s"
                self.db.execute(delete_sql, (token,))
                return {'success': False, 'message': 'Token已过期'}

            # 获取用户信息
            user = self.get_user_by_id(result['user_id'])
            if not user:
                return {'success': False, 'message': '用户不存在'}

            return {
                'success': True,
                'user_id': user['id'],
                'username': user['username']
            }
        except Exception as e:
            return {'success': False, 'message': f'验证失败: {str(e)}'}

    def logout(self, token):
        """
        退出登录 - 删除会话

        参数:
            token: 会话token

        返回:
            字典，包含success和message字段
        """
        try:
            sql = "DELETE FROM user_sessions WHERE session_token = %s"
            self.db.execute(sql, (token,))
            return {'success': True, 'message': '已退出登录'}
        except Exception as e:
            return {'success': False, 'message': f'退出失败: {str(e)}'}

    def get_user_by_username(self, username):
        """
        通过用户名获取用户

        参数:
            username: 用户名

        返回:
            用户字典，或None
        """
        try:
            sql = """
                SELECT id, username, password_hash, phone, created_at, last_login
                FROM users
                WHERE username = %s
            """
            result = self.db.query_one(sql, (username,))
            return result
        except Exception as e:
            print(f"查询用户失败: {e}")
            return None

    def get_user_by_id(self, user_id):
        """
        通过ID获取用户

        参数:
            user_id: 用户ID

        返回:
            用户字典，或None
        """
        try:
            sql = """
                SELECT id, username, password_hash, phone, avatar_url, chat_background, created_at, last_login
                FROM users
                WHERE id = %s
            """
            result = self.db.query_one(sql, (user_id,))
            return result
        except Exception as e:
            print(f"查询用户失败: {e}")
            return None

    def change_password(self, user_id, old_password, new_password):
        """
        修改用户密码

        参数:
            user_id: 用户ID
            old_password: 原密码（明文）
            new_password: 新密码（明文）

        返回:
            字典，包含success和message字段
        """
        try:
            # 1. 验证旧密码
            user = self.get_user_by_id(user_id)
            if not user:
                return {'success': False, 'message': '用户不存在'}

            # 注意：数据库中的字段是password_hash，但验证时使用password
            old_password_hash = self.hash_password(old_password)
            if user.get('password_hash') != old_password_hash and user.get('password') != old_password_hash:
                return {'success': False, 'message': '原密码错误'}

            # 2. 更新密码
            new_password_hash = self.hash_password(new_password)
            sql = "UPDATE users SET password_hash=%s WHERE id=%s"
            self.db.execute(sql, [new_password_hash, user_id])

            # 3. 清除所有会话（强制重新登录）
            self.db.execute("DELETE FROM user_sessions WHERE user_id=%s", [user_id])

            return {'success': True, 'message': '密码修改成功，请重新登录'}
        except Exception as e:
            print(f"修改密码失败: {e}")
            return {'success': False, 'message': f'修改密码失败: {str(e)}'}

    def clean_expired_sessions(self):
        """
        清理过期的会话记录

        删除所有expires_at时间早于当前时间的会话
        """
        try:
            sql = """
                DELETE FROM user_sessions
                WHERE expires_at < %s
            """
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db.execute(sql, (now,))
            print("✅ 过期会话已清理")
        except Exception as e:
            print(f"清理过期会话失败: {e}")

    def update_avatar(self, user_id, avatar_url):
        """
        更新用户头像

        参数:
            user_id: 用户ID
            avatar_url: 头像URL路径

        返回:
            是否成功
        """
        try:
            sql = """
                UPDATE users
                SET avatar_url = %s
                WHERE id = %s
            """
            self.db.execute(sql, (avatar_url, user_id))
            print(f"✅ 用户头像已更新: user_id={user_id}, avatar={avatar_url}")
            return True
        except Exception as e:
            print(f"更新用户头像失败: {e}")
            return False

    def update_phone(self, user_id, phone):
        """
        更新用户手机号

        参数:
            user_id: 用户ID
            phone: 手机号码

        返回:
            是否成功
        """
        try:
            sql = """
                UPDATE users
                SET phone = %s
                WHERE id = %s
            """
            self.db.execute(sql, (phone, user_id))
            print(f"✅ 用户手机号已更新: user_id={user_id}, phone={phone}")
            return True
        except Exception as e:
            print(f"更新用户手机号失败: {e}")
            return False

    def update_theme(self, user_id, theme):
        """
        更新用户主题

        参数:
            user_id: 用户ID
            theme: 主题名称 (light/dark/auto/candy/sunset/ocean)

        返回:
            是否成功
        """
        try:
            sql = """
                UPDATE users
                SET theme = %s
                WHERE id = %s
            """
            self.db.execute(sql, (theme, user_id))
            print(f"✅ 用户主题已更新: user_id={user_id}, theme={theme}")
            return True
        except Exception as e:
            print(f"更新用户主题失败: {e}")
            return False

    def update_chat_background(self, user_id, chat_background):
        """
        更新用户对话背景

        参数:
            user_id: 用户ID
            chat_background: 对话背景URL路径

        返回:
            是否成功
        """
        try:
            sql = """
                UPDATE users
                SET chat_background = %s
                WHERE id = %s
            """
            self.db.execute(sql, (chat_background, user_id))
            print(f"✅ 用户对话背景已更新: user_id={user_id}, chat_background={chat_background}")
            return True
        except Exception as e:
            print(f"更新用户对话背景失败: {e}")
            return False

    def update_settings(self, user_id, chat_background=None):
        """
        更新用户设置

        参数:
            user_id: 用户ID
            chat_background: 聊天背景颜色 (十六进制代码)

        返回:
            是否成功
        """
        try:
            updates = []
            params = []

            if chat_background is not None:
                updates.append("chat_background = %s")
                params.append(chat_background)

            if not updates:
                return True

            params.append(user_id)
            sql = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"

            self.db.execute(sql, tuple(params))
            return True
        except Exception as e:
            print(f"更新用户设置失败: {e}")
            return False

    def register_with_verification(self, username, password, email='', phone='',
                                   email_verified=False, phone_verified=False):
        """
        注册新用户（带验证状态）- 用于邮箱/手机验证码注册流程

        参数:
            username: 用户名
            password: 密码（明文，将被哈希）
            email: 邮箱地址（可选）
            phone: 电话号码（可选）
            email_verified: 邮箱是否已验证
            phone_verified: 手机号是否已验证

        返回:
            字典，包含success、message、user_id字段
        """
        # 检查用户名是否已存在
        existing_user = self.get_user_by_username(username)
        if existing_user:
            return {'success': False, 'message': '用户名已存在'}

        # 检查邮箱是否已存在（如果提供了邮箱）
        if email:
            existing_email = self.db.query_one("SELECT id FROM users WHERE email = %s", (email,))
            if existing_email:
                return {'success': False, 'message': '邮箱已被注册'}

        # 检查手机是否已存在（如果提供了手机号）
        if phone:
            existing_phone = self.db.query_one("SELECT id FROM users WHERE phone = %s", (phone,))
            if existing_phone:
                return {'success': False, 'message': '手机号已被注册'}

        try:
            # 插入新用户记录，包含验证状态
            sql = """
                INSERT INTO users
                (username, password_hash, email, phone, email_verified, phone_verified, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            user_id = self.db.execute(sql, (
                username,
                self.hash_password(password),
                email or None,  # 如果为空则存储NULL
                phone or None,  # 如果为空则存储NULL
                1 if email_verified else 0,
                1 if phone_verified else 0,
                now
            ))

            print(f"✅ 用户注册成功: username={username}, user_id={user_id}")
            return {
                'success': True,
                'message': '注册成功',
                'user_id': user_id
            }
        except Exception as e:
            print(f"❌ 注册失败: {str(e)}")
            return {'success': False, 'message': f'注册失败: {str(e)}'}

    def get_user_by_email(self, email):
        """
        通过邮箱获取用户

        参数:
            email: 邮箱地址

        返回:
            用户字典，或None
        """
        try:
            sql = """
                SELECT id, username, password_hash, email, phone,
                       email_verified, phone_verified, created_at, last_login
                FROM users
                WHERE email = %s
            """
            result = self.db.query_one(sql, (email,))
            return result
        except Exception as e:
            print(f"查询用户失败: {e}")
            return None

    def get_user_by_phone(self, phone):
        """
        通过手机号获取用户

        参数:
            phone: 手机号

        返回:
            用户字典，或None
        """
        try:
            sql = """
                SELECT id, username, password_hash, email, phone,
                       email_verified, phone_verified, created_at, last_login
                FROM users
                WHERE phone = %s
            """
            result = self.db.query_one(sql, (phone,))
            return result
        except Exception as e:
            print(f"查询用户失败: {e}")
            return None

