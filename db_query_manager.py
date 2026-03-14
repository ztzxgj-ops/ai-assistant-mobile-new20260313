#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查询管理器
支持同时查询本地和服务器数据库，并进行数据对比
"""

import pymysql
from pymysql.cursors import DictCursor
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional


class DatabaseQueryManager:
    """双数据库查询管理器"""

    def __init__(self, local_config_file='mysql_config.json',
                 server_config_file='mysql_config_server.json'):
        """初始化本地和服务器数据库连接"""
        try:
            self.local_config = self._load_config(local_config_file)
            self.server_config = self._load_config(server_config_file)

            self.local_conn = None
            self.server_conn = None

            self._connect_local()
            self._connect_server()
        except Exception as e:
            print(f"⚠️ 数据库查询管理器初始化警告: {e}")
            self.local_config = None
            self.server_config = None
            self.local_conn = None
            self.server_conn = None

    def _load_config(self, config_file):
        """加载数据库配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ 配置文件不存在: {config_file}")
            return None

    def _connect_local(self):
        """连接本地数据库"""
        if not self.local_config:
            return
        try:
            self.local_conn = pymysql.connect(
                host=self.local_config['host'],
                port=self.local_config.get('port', 3306),
                user=self.local_config['user'],
                password=self.local_config['password'],
                database=self.local_config['database'],
                charset=self.local_config.get('charset', 'utf8mb4'),
                cursorclass=DictCursor
            )
            print(f"✅ 本地数据库已连接: {self.local_config['host']}")
        except Exception as e:
            print(f"❌ 本地数据库连接失败: {e}")
            self.local_conn = None

    def _connect_server(self):
        """连接服务器数据库"""
        if not self.server_config:
            return
        try:
            self.server_conn = pymysql.connect(
                host=self.server_config['host'],
                port=self.server_config.get('port', 3306),
                user=self.server_config['user'],
                password=self.server_config['password'],
                database=self.server_config['database'],
                charset=self.server_config.get('charset', 'utf8mb4'),
                cursorclass=DictCursor
            )
            print(f"✅ 服务器数据库已连接: {self.server_config['host']}")
        except Exception as e:
            print(f"❌ 服务器数据库连接失败: {e}")
            self.server_conn = None

    def _execute_query(self, conn, sql, params=None):
        """执行查询"""
        if not conn:
            return []
        try:
            conn.ping(reconnect=True)
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return []

    def query_subcategories(self, user_id, source='both', limit=100):
        """查询子类别数据

        Args:
            user_id: 用户ID
            source: 'local', 'server', 'both'
            limit: 查询条数限制

        Returns:
            dict: {'local': [...], 'server': [...]}
        """
        sql = """
            SELECT id, category_id, name, code, description,
                   sort_order, user_id, created_at, updated_at
            FROM subcategories
            WHERE user_id = %s OR user_id IS NULL
            ORDER BY created_at DESC
            LIMIT %s
        """

        result = {'local': [], 'server': []}

        if source in ['local', 'both']:
            if self.local_conn:
                result['local'] = self._execute_query(self.local_conn, sql, (user_id, limit))
            else:
                # 返回演示数据
                result['local'] = self._get_demo_subcategories()

        if source in ['server', 'both']:
            if self.server_conn:
                result['server'] = self._execute_query(self.server_conn, sql, (user_id, limit))
            else:
                # 返回演示数据
                result['server'] = self._get_demo_subcategories()

        return result

    def query_daily_records(self, user_id, source='both', limit=100,
                           time_range=None, status=None):
        """查询日常记录数据

        Args:
            user_id: 用户ID
            source: 'local', 'server', 'both'
            limit: 查询条数限制
            time_range: 时间范围 ('24h', '7d', '30d', 'all')
            status: 状态过滤 ('pending', 'completed')

        Returns:
            dict: {'local': [...], 'server': [...]}
        """
        conditions = ["user_id = %s"]
        params = [user_id]

        # 时间范围过滤
        if time_range and time_range != 'all':
            if time_range == '24h':
                time_delta = timedelta(hours=24)
            elif time_range == '7d':
                time_delta = timedelta(days=7)
            elif time_range == '30d':
                time_delta = timedelta(days=30)
            else:
                time_delta = None

            if time_delta:
                cutoff_time = datetime.now() - time_delta
                conditions.append("created_at >= %s")
                params.append(cutoff_time)

        # 状态过滤
        if status:
            conditions.append("status = %s")
            params.append(status)

        sql = f"""
            SELECT id, user_id, subcategory_id, title, content,
                   record_date, mood, weather, tags, is_private,
                   status, completed_at, sort_order, created_at, updated_at
            FROM daily_records
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT %s
        """
        params.append(limit)

        result = {'local': [], 'server': []}

        if source in ['local', 'both']:
            if self.local_conn:
                result['local'] = self._execute_query(self.local_conn, sql, tuple(params))
            else:
                # 返回演示数据
                result['local'] = self._get_demo_daily_records()

        if source in ['server', 'both']:
            if self.server_conn:
                result['server'] = self._execute_query(self.server_conn, sql, tuple(params))
            else:
                # 返回演示数据
                result['server'] = self._get_demo_daily_records()

        return result

    def compare_data(self, local_data, server_data, key_field='id'):
        """对比本地和服务器数据差异

        Returns:
            dict: {
                'only_local': [...],      # 仅本地有
                'only_server': [...],     # 仅服务器有
                'both': [...],            # 两边都有
                'different': [...]        # 内容不同
            }
        """
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

    def get_statistics(self, user_id):
        """获取数据统计信息"""
        stats = {
            'local': {'subcategories': 0, 'daily_records': 0},
            'server': {'subcategories': 0, 'daily_records': 0}
        }

        # 统计子类别
        if self.local_conn:
            sql = "SELECT COUNT(*) as count FROM subcategories WHERE user_id = %s OR user_id IS NULL"
            result = self._execute_query(self.local_conn, sql, (user_id,))
            stats['local']['subcategories'] = result[0]['count'] if result else 0
        else:
            stats['local']['subcategories'] = len(self._get_demo_subcategories())

        if self.server_conn:
            sql = "SELECT COUNT(*) as count FROM subcategories WHERE user_id = %s OR user_id IS NULL"
            result = self._execute_query(self.server_conn, sql, (user_id,))
            stats['server']['subcategories'] = result[0]['count'] if result else 0
        else:
            stats['server']['subcategories'] = len(self._get_demo_subcategories())

        # 统计日常记录
        if self.local_conn:
            sql = "SELECT COUNT(*) as count FROM daily_records WHERE user_id = %s"
            result = self._execute_query(self.local_conn, sql, (user_id,))
            stats['local']['daily_records'] = result[0]['count'] if result else 0
        else:
            stats['local']['daily_records'] = len(self._get_demo_daily_records())

        if self.server_conn:
            sql = "SELECT COUNT(*) as count FROM daily_records WHERE user_id = %s"
            result = self._execute_query(self.server_conn, sql, (user_id,))
            stats['server']['daily_records'] = result[0]['count'] if result else 0
        else:
            stats['server']['daily_records'] = len(self._get_demo_daily_records())

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
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'id': 2,
                'category_id': 2,
                'name': '个人日记',
                'code': 'personal_diary',
                'description': '个人日记记录',
                'sort_order': 2,
                'user_id': None,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'id': 3,
                'category_id': 3,
                'name': '财务记录',
                'code': 'finance',
                'description': '财务相关记录',
                'sort_order': 3,
                'user_id': None,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
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
                'record_date': datetime.now().date(),
                'mood': '开心',
                'weather': '晴天',
                'tags': '工作,报告',
                'is_private': False,
                'status': 'completed',
                'completed_at': datetime.now(),
                'sort_order': 1,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'id': 2,
                'user_id': 1,
                'subcategory_id': 2,
                'title': '今日感悟',
                'content': '今天学到了很多新的技术知识，收获很大',
                'record_date': datetime.now().date(),
                'mood': '满足',
                'weather': '多云',
                'tags': '学习,技术',
                'is_private': False,
                'status': 'pending',
                'completed_at': None,
                'sort_order': 2,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'id': 3,
                'user_id': 1,
                'subcategory_id': 3,
                'title': '月度支出统计',
                'content': '本月支出总计5000元，其中食物2000元，交通1500元，其他1500元',
                'record_date': datetime.now().date(),
                'mood': '平静',
                'weather': '晴天',
                'tags': '财务,统计',
                'is_private': True,
                'status': 'completed',
                'completed_at': datetime.now(),
                'sort_order': 3,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
        ]

    def close(self):
        """关闭数据库连接"""
        if self.local_conn:
            self.local_conn.close()
        if self.server_conn:
            self.server_conn.close()
