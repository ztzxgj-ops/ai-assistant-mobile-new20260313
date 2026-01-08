#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用户管理模块 - SQLite版本"""

import hashlib
import secrets
from datetime import datetime, timedelta
from sqlite_manager import SQLiteManager


class UserManager:
    """基于SQLite的用户管理器"""

    def __init__(self, db_manager):
        """
        初始化用户管理器

        参数:
            db_manager: SQLiteManager实例，用于数据库操作
        """
        if not isinstance(db_manager, SQLiteManager):
            raise ValueError("db_manager must be an instance of SQLiteManager")

        self.db = db_manager
        print("✅ 使用SQLite用户管理器")

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
                INSERT INTO users (username, password, phone, created_at)
                VALUES (?, ?, ?, ?)
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

        # 验证密码（兼容password和password_hash两种字段名）
        password_field = user.get('password') or user.get('password_hash')
        if password_field != self.hash_password(password):
            return {'success': False, 'message': '密码错误'}

        try:
            # 更新最后登录时间
            update_sql = "UPDATE users SET last_login = ? WHERE id = ?"
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db.execute(update_sql, (now, user['id']))

            # 生成token并创建会话
            token = self.generate_token()
            insert_sql = """
                INSERT INTO sessions (user_id, username, token, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?)
            """
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            expires_at = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

            self.db.execute(insert_sql, (
                user['id'],
                user['username'],
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
                FROM sessions
                WHERE token = ?
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
                delete_sql = "DELETE FROM sessions WHERE token = ?"
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
            sql = "DELETE FROM sessions WHERE token = ?"
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
                SELECT id, username, password, phone, created_at, last_login
                FROM users
                WHERE username = ?
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
                SELECT id, username, password, phone, created_at, last_login
                FROM users
                WHERE id = ?
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

            # 验证旧密码
            old_password_hash = self.hash_password(old_password)
            if user.get('password') != old_password_hash:
                return {'success': False, 'message': '原密码错误'}

            # 2. 更新密码
            new_password_hash = self.hash_password(new_password)
            sql = "UPDATE users SET password = ? WHERE id = ?"
            self.db.execute(sql, (new_password_hash, user_id))

            # 3. 清除所有会话（强制重新登录）
            self.db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

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
                DELETE FROM sessions
                WHERE expires_at < ?
            """
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db.execute(sql, (now,))
            print("✅ 过期会话已清理")
        except Exception as e:
            print(f"清理过期会话失败: {e}")
