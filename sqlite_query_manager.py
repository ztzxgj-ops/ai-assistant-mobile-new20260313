#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite数据库查询管理器
支持查询本地SQLite数据库，用于演示和开发
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class SQLiteQueryManager:
    """SQLite数据库查询管理器"""

    def __init__(self, db_path='data.db'):
        """初始化SQLite连接"""
        self.db_path = db_path
        self.conn = None
        self._connect()

    def _connect(self):
        """连接SQLite数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            print(f"✅ SQLite数据库已连接: {self.db_path}")
        except Exception as e:
            print(f"❌ SQLite连接失败: {e}")
            self.conn = None

    def _execute_query(self, sql, params=None):
        """执行查询"""
        if not self.conn:
            return []
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params or ())
            results = cursor.fetchall()
            cursor.close()
            # 转换为字典列表
            return [dict(row) for row in results]
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return []

    def query_subcategories(self, user_id=None, limit=100):
        """查询子类别数据"""
        sql = """
            SELECT id, category_id, name, code, description,
                   sort_order, user_id, created_at, updated_at
            FROM subcategories
            ORDER BY created_at DESC
            LIMIT ?
        """
        result = self._execute_query(sql, (limit,))
        return result if result else self._get_demo_subcategories()

    def query_daily_records(self, user_id=None, limit=100,
                           time_range=None, status=None):
        """查询日常记录数据"""
        sql = """
            SELECT id, user_id, subcategory_id, title, content,
                   record_date, mood, weather, tags, is_private,
                   status, completed_at, sort_order, created_at, updated_at
            FROM daily_records
            ORDER BY created_at DESC
            LIMIT ?
        """
        result = self._execute_query(sql, (limit,))
        return result if result else self._get_demo_daily_records()

    def compare_data(self, local_data, server_data, key_field='id'):
        """对比本地和服务器数据差异"""
        local_dict = {item[key_field]: item for item in local_data}
        server_dict = {item[key_field]: item for item in server_data}

        local_ids = set(local_dict.keys())
        server_ids = set(server_dict.keys())

        result = {
            'only_local': [local_dict[id] for id in (local_ids - server_ids)],
            'only_server': [server_dict[id] for id in (server_ids - local_ids)],
            'both': [],
            'different': []
        }

        # 检查共同ID的数据是否一致
        common_ids = local_ids & server_ids
        for id in common_ids:
            local_item = local_dict[id]
            server_item = server_dict[id]

            # 比较关键字段（排除时间戳）
            is_different = False
            diff_fields = []

            for key in local_item.keys():
                if key in ['created_at', 'updated_at']:
                    continue
                if local_item.get(key) != server_item.get(key):
                    is_different = True
                    diff_fields.append(key)

            if is_different:
                result['different'].append({
                    'id': id,
                    'local': local_item,
                    'server': server_item,
                    'diff_fields': diff_fields
                })
            else:
                result['both'].append(local_item)

        return result

    def get_statistics(self, user_id=None):
        """获取数据统计信息"""
        stats = {
            'local': {'subcategories': 0, 'daily_records': 0},
            'server': {'subcategories': 0, 'daily_records': 0}
        }

        if self.conn:
            # 统计子类别
            sql = "SELECT COUNT(*) as count FROM subcategories"
            result = self._execute_query(sql)
            stats['local']['subcategories'] = result[0]['count'] if result else 0

            # 统计日常记录
            sql = "SELECT COUNT(*) as count FROM daily_records"
            result = self._execute_query(sql)
            stats['local']['daily_records'] = result[0]['count'] if result else 0
        else:
            # 使用演示数据
            stats['local']['subcategories'] = len(self._get_demo_subcategories())
            stats['local']['daily_records'] = len(self._get_demo_daily_records())

        # 服务器数据与本地相同（演示模式）
        stats['server'] = stats['local'].copy()

        return stats

    def _get_demo_subcategories(self):
        """返回演示数据 - 子类别"""
        return [
            {
                'id': 1,
                'category_id': 1,
                'name': '工作任务',
                'code': 'work_task',
                'description': '日常工作任务',
                'sort_order': 1,
                'user_id': None,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'id': 2,
                'category_id': 2,
                'name': '个人日记',
                'code': 'personal_diary',
                'description': '个人日记记录',
                'sort_order': 2,
                'user_id': None,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'id': 3,
                'category_id': 3,
                'name': '财务记录',
                'code': 'finance',
                'description': '财务相关记录',
                'sort_order': 3,
                'user_id': None,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        ]

    def _get_demo_daily_records(self):
        """返回演示数据 - 日常记录"""
        return [
            {
                'id': 1,
                'user_id': 1,
                'subcategory_id': 1,
                'title': '完成项目报告',
                'content': '今天完成了Q1季度的项目报告，已提交给经理审核',
                'record_date': datetime.now().strftime('%Y-%m-%d'),
                'mood': '开心',
                'weather': '晴天',
                'tags': '工作,报告',
                'is_private': 0,
                'status': 'completed',
                'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sort_order': 1,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'id': 2,
                'user_id': 1,
                'subcategory_id': 2,
                'title': '今日感悟',
                'content': '今天学到了很多新的技术知识，收获很大',
                'record_date': datetime.now().strftime('%Y-%m-%d'),
                'mood': '满足',
                'weather': '多云',
                'tags': '学习,技术',
                'is_private': 0,
                'status': 'pending',
                'completed_at': None,
                'sort_order': 2,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'id': 3,
                'user_id': 1,
                'subcategory_id': 3,
                'title': '月度支出统计',
                'content': '本月支出总计5000元，其中食物2000元，交通1500元，其他1500元',
                'record_date': datetime.now().strftime('%Y-%m-%d'),
                'mood': '平静',
                'weather': '晴天',
                'tags': '财务,统计',
                'is_private': 1,
                'status': 'completed',
                'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sort_order': 3,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        ]

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
