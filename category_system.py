#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分类管理系统
支持8大类别的层级管理：工作、计划、财务、账号密码、提醒、文件、记录、时间
"""

from mysql_manager import MySQLManager


class CategoryManager(MySQLManager):
    """类别管理器"""

    def __init__(self, config_file='mysql_config.json'):
        super().__init__(config_file)
        print("✅ 类别管理器已初始化")

    def get_all_categories(self, user_id=None):
        """获取所有一级类别"""
        query = "SELECT * FROM categories ORDER BY sort_order, id"
        return self.query(query)

    def get_category_by_code(self, code):
        """根据代码获取类别"""
        query = "SELECT * FROM categories WHERE code = %s"
        results = self.query(query, (code,))
        return results[0] if results else None

    def get_subcategories(self, category_id, user_id=None):
        """获取指定类别的子类别"""
        if user_id:
            # 获取系统默认 + 用户自定义的子类别
            query = """
                SELECT * FROM subcategories
                WHERE category_id = %s AND (user_id IS NULL OR user_id = %s)
                ORDER BY sort_order, id
            """
            return self.query(query, (category_id, user_id))
        else:
            # 只获取系统默认子类别
            query = """
                SELECT * FROM subcategories
                WHERE category_id = %s AND user_id IS NULL
                ORDER BY sort_order, id
            """
            return self.query(query, (category_id,))

    def add_category(self, name, code, icon='', description='', user_id=None):
        """添加自定义一级类别（仅管理员）"""
        query = """
            INSERT INTO categories (name, code, icon, description, is_system)
            VALUES (%s, %s, %s, %s, FALSE)
        """
        return self.execute(query, (name, code, icon, description))

    def add_subcategory(self, category_id, name, code, description='', user_id=None):
        """添加子类别"""
        query = """
            INSERT INTO subcategories (category_id, name, code, description, user_id)
            VALUES (%s, %s, %s, %s, %s)
        """
        return self.execute(query, (category_id, name, code, description, user_id))

    def delete_subcategory(self, subcategory_id, user_id):
        """删除子类别（仅用户自己创建的）"""
        query = "DELETE FROM subcategories WHERE id = %s AND user_id = %s"
        return self.execute(query, (subcategory_id, user_id))

    def get_category_tree(self, user_id=None):
        """获取完整的类别树结构"""
        categories = self.get_all_categories(user_id)
        tree = []

        for category in categories:
            subcategories = self.get_subcategories(category['id'], user_id)
            tree.append({
                'id': category['id'],
                'name': category['name'],
                'code': category['code'],
                'icon': category['icon'],
                'description': category['description'],
                'subcategories': subcategories
            })

        return tree


class WorkTaskManager(MySQLManager):
    """工作任务管理器"""

    def __init__(self, config_file='mysql_config.json'):
        super().__init__(config_file)

    def add_task(self, user_id, title, content='', priority='medium',
                 subcategory_id=None, due_date=None):
        """添加工作任务"""
        query = """
            INSERT INTO work_tasks
            (user_id, title, content, priority, subcategory_id, due_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        """
        return self.execute(query, (user_id, title, content, priority, subcategory_id, due_date))

    def list_tasks(self, user_id, status=None, subcategory_id=None):
        """列出任务"""
        if status:
            if subcategory_id:
                query = """
                    SELECT * FROM work_tasks
                    WHERE user_id = %s AND status = %s AND subcategory_id = %s
                    ORDER BY sort_order DESC, priority DESC, created_at DESC
                """
                result = self.query(query, (user_id, status, subcategory_id))
            else:
                query = """
                    SELECT * FROM work_tasks
                    WHERE user_id = %s AND status = %s
                    ORDER BY sort_order DESC, priority DESC, created_at DESC
                """
                result = self.query(query, (user_id, status))
        else:
            query = """
                SELECT * FROM work_tasks
                WHERE user_id = %s
                ORDER BY sort_order DESC, priority DESC, created_at DESC
            """
            result = self.query(query, (user_id,))

        # ✨ 添加 source 字段，标识数据来源
        for task in result:
            task['source'] = 'work_tasks'

        # 按标题中的"紧急"和"重要"关键词排序，同时考虑sort_order
        def sort_key(task):
            title = task.get('title', '')
            sort_order = task.get('sort_order', 0)  # 默认为0

            if '紧急' in title:
                priority = 0  # 紧急排在最前
            elif '重要' in title:
                priority = 1  # 重要排在第二
            else:
                priority = 2  # 普通排在最后

            # 返回元组：先按优先级排序，再按sort_order降序排序
            return (priority, -sort_order)

        result.sort(key=sort_key)

        return result

    def update_task_status(self, task_id, status, user_id):
        """更新任务状态"""
        query = """
            UPDATE work_tasks
            SET status = %s, completed_at = IF(%s = 'completed', NOW(), NULL)
            WHERE id = %s AND user_id = %s
        """
        print(f"🔍 [SQL] 执行更新: task_id={task_id}, status={status}, user_id={user_id}")
        result = self.execute(query, (status, status, task_id, user_id))
        print(f"🔍 [SQL] 更新影响行数: {result}")
        return result

    def update_task_order(self, task_id, sort_order, user_id):
        """更新任务排序"""
        query = "UPDATE work_tasks SET sort_order = %s WHERE id = %s AND user_id = %s"
        return self.execute(query, (sort_order, task_id, user_id))

    def delete_task(self, task_id, user_id):
        """删除任务"""
        query = "DELETE FROM work_tasks WHERE id = %s AND user_id = %s"
        return self.execute(query, (task_id, user_id))


class FinanceManager(MySQLManager):
    """财务记录管理器"""

    def __init__(self, config_file='mysql_config.json'):
        super().__init__(config_file)

    def add_record(self, user_id, type, amount, title, description='',
                   record_date=None, subcategory_id=None, tags=''):
        """添加财务记录"""
        if not record_date:
            from datetime import datetime
            record_date = datetime.now().strftime('%Y-%m-%d')

        query = """
            INSERT INTO finance_records
            (user_id, type, amount, title, description, record_date, subcategory_id, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute(query, (user_id, type, amount, title, description,
                                   record_date, subcategory_id, tags))

    def list_records(self, user_id, type=None, start_date=None, end_date=None, status='pending'):
        """列出财务记录"""
        conditions = ["user_id = %s"]
        params = [user_id]

        if type:
            conditions.append("type = %s")
            params.append(type)
        if start_date:
            conditions.append("record_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("record_date <= %s")
            params.append(end_date)
        if status:
            conditions.append("status = %s")
            params.append(status)

        query = f"""
            SELECT * FROM finance_records
            WHERE {' AND '.join(conditions)}
            ORDER BY record_date DESC, created_at DESC
        """
        return self.query(query, tuple(params))

    def get_summary(self, user_id, start_date=None, end_date=None):
        """获取财务汇总"""
        conditions = ["user_id = %s"]
        params = [user_id]

        if start_date:
            conditions.append("record_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("record_date <= %s")
            params.append(end_date)

        query = f"""
            SELECT
                type,
                SUM(amount) as total,
                COUNT(*) as count
            FROM finance_records
            WHERE {' AND '.join(conditions)}
            GROUP BY type
        """
        return self.query(query, tuple(params))


    def update_finance_status(self, record_id, status, user_id):
        """更新财务记录状态"""
        query = """
            UPDATE finance_records
            SET status = %s, completed_at = IF(%s = 'completed', NOW(), NULL)
            WHERE id = %s AND user_id = %s
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, (status, status, record_id, user_id))
            return cursor.rowcount > 0

    def delete_finance_record(self, record_id, user_id):
        """删除财务记录"""
        query = "DELETE FROM finance_records WHERE id = %s AND user_id = %s"
        return self.execute(query, (record_id, user_id))


class AccountManager(MySQLManager):
    """账号密码管理器"""

    def __init__(self, config_file='mysql_config.json'):
        super().__init__(config_file)

    def add_account(self, user_id, platform, account, password,
                   email='', phone='', notes='', url='', subcategory_id=None, tags=''):
        """添加账号（密码需要加密）"""
        # 简单加密（实际应使用更安全的加密方式）
        import base64
        password_encrypted = base64.b64encode(password.encode()).decode()

        query = """
            INSERT INTO account_credentials
            (user_id, platform, account, password_encrypted, email, phone,
             notes, url, subcategory_id, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute(query, (user_id, platform, account, password_encrypted,
                                   email, phone, notes, url, subcategory_id, tags))

    def list_accounts(self, user_id, subcategory_id=None, status='pending'):
        """列出账号（不返回密码）"""
        conditions = ["user_id = %s"]
        params = [user_id]

        if subcategory_id:
            conditions.append("subcategory_id = %s")
            params.append(subcategory_id)
        if status:
            conditions.append("status = %s")
            params.append(status)

        query = f"""
            SELECT id, platform, account, email, phone, url, tags, created_at
            FROM account_credentials
            WHERE {' AND '.join(conditions)}
            ORDER BY platform, created_at DESC
        """
        return self.query(query, tuple(params))

    def get_account_detail(self, account_id, user_id):
        """获取账号详情（包含密码，需要验证）"""
        query = """
            SELECT * FROM account_credentials
            WHERE id = %s AND user_id = %s
        """
        results = self.query(query, (account_id, user_id))
        if results:
            account = results[0]
            # 解密密码
            import base64
            account['password'] = base64.b64decode(account['password_encrypted']).decode()
            return account
        return None

    def update_account_status(self, account_id, status, user_id):
        """更新账号状态"""
        query = """
            UPDATE account_credentials
            SET status = %s, completed_at = IF(%s = 'completed', NOW(), NULL)
            WHERE id = %s AND user_id = %s
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, (status, status, account_id, user_id))
            return cursor.rowcount > 0

    def delete_account(self, account_id, user_id):
        """删除账号"""
        query = "DELETE FROM account_credentials WHERE id = %s AND user_id = %s"
        return self.execute(query, (account_id, user_id))


class DailyRecordManager(MySQLManager):
    """日常记录管理器"""

    def __init__(self, config_file='mysql_config.json'):
        super().__init__(config_file)

    def add_record(self, user_id, content, title='', record_date=None,
                   subcategory_id=None, mood='', weather='', tags='', is_private=False):
        """添加记录"""
        # ✨ 防止创建空记录：title 和 content 都为空时不添加
        if (not title or title.strip() == '') and (not content or content.strip() == ''):
            print(f"⚠️ 警告：尝试创建空记录，已拒绝")
            return None

        # ✨ 检查用户的存储模式，如果是local则不保存到云端数据库
        if user_id:
            check_sql = "SELECT storage_mode FROM users WHERE id = %s"
            user_result = self.query(check_sql, (user_id,))
            if user_result and user_result[0].get('storage_mode') == 'local':
                print(f"⚠️ 用户{user_id}使用本地存储模式，跳过云端记录保存")
                return None

        if not record_date:
            from datetime import datetime
            record_date = datetime.now().strftime('%Y-%m-%d')

        query = """
            INSERT INTO daily_records
            (user_id, title, content, record_date, subcategory_id,
             mood, weather, tags, is_private)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute(query, (user_id, title, content, record_date,
                                   subcategory_id, mood, weather, tags, is_private))

    def list_records(self, user_id, subcategory_id=None, start_date=None, end_date=None, status=None):
        """列出记录"""
        conditions = ["user_id = %s"]
        params = [user_id]

        if subcategory_id:
            conditions.append("subcategory_id = %s")
            params.append(subcategory_id)
        if start_date:
            conditions.append("record_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("record_date <= %s")
            params.append(end_date)
        if status:
            conditions.append("status = %s")
            params.append(status)

        # ✨ 过滤掉 title 和 content 都为空的记录（必须用括号包裹整个条件）
        conditions.append("((title IS NOT NULL AND title != '') OR (content IS NOT NULL AND content != ''))")

        query = f"""
            SELECT * FROM daily_records
            WHERE {' AND '.join(conditions)}
            ORDER BY
                CASE
                    WHEN title LIKE '%%紧急%%' OR title LIKE '%%urgent%%' THEN 0
                    WHEN title LIKE '%%重要%%' OR title LIKE '%%important%%' THEN 1
                    ELSE 2
                END,
                sort_order DESC,
                record_date DESC,
                created_at DESC
        """
        print(f"🔍 DEBUG list_records: query={query}, params={tuple(params)}")
        result = self.query(query, tuple(params))
        print(f"🔍 DEBUG list_records: 返回{len(result)}条记录")

        # ✨ 添加 source 字段，标识数据来源
        for record in result:
            record['source'] = 'daily_records'

        return result

    def search_records(self, user_id, keyword):
        """搜索记录"""
        query = """
            SELECT * FROM daily_records
            WHERE user_id = %s AND (title LIKE %s OR content LIKE %s) AND status != 'completed'
            ORDER BY record_date DESC
        """
        pattern = f"%{keyword}%"
        result = self.query(query, (user_id, pattern, pattern))

        # ✨ 添加 source 字段，标识数据来源
        for record in result:
            record['source'] = 'daily_records'

        return result

    def delete_record(self, record_id, user_id):
        """删除记录"""
        query = "DELETE FROM daily_records WHERE id = %s AND user_id = %s"
        return self.execute(query, (record_id, user_id))

    def update_record_status(self, record_id, status, user_id):
        """更新记录状态"""
        query = """
            UPDATE daily_records
            SET status = %s, completed_at = IF(%s = 'completed', NOW(), NULL)
            WHERE id = %s AND user_id = %s
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, (status, status, record_id, user_id))
            return cursor.rowcount > 0  # 返回是否有行被更新

    def update_record_title(self, record_id, title, user_id):
        """更新记录标题"""
        query = """
            UPDATE daily_records
            SET title = %s, content = %s
            WHERE id = %s AND user_id = %s
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, (title, title, record_id, user_id))
            return cursor.rowcount > 0  # 返回是否有行被更新


class TimeScheduleManager(MySQLManager):
    """时间规划管理器"""

    def __init__(self, config_file='mysql_config.json'):
        super().__init__(config_file)

    def add_schedule(self, user_id, title, schedule_date, start_time, end_time,
                    description='', subcategory_id=None, tags=''):
        """添加时间规划"""
        query = """
            INSERT INTO time_schedules
            (user_id, title, description, schedule_date, start_time, end_time,
             subcategory_id, tags, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
        """
        return self.execute(query, (user_id, title, description, schedule_date,
                                   start_time, end_time, subcategory_id, tags))

    def list_schedules(self, user_id, schedule_date=None, subcategory_id=None, status='pending'):
        """列出时间规划"""
        conditions = ["user_id = %s"]
        params = [user_id]

        if schedule_date:
            conditions.append("schedule_date = %s")
            params.append(schedule_date)
        if subcategory_id:
            conditions.append("subcategory_id = %s")
            params.append(subcategory_id)
        if status:
            conditions.append("status = %s")
            params.append(status)

        query = f"""
            SELECT * FROM time_schedules
            WHERE {' AND '.join(conditions)}
            ORDER BY schedule_date DESC, start_time ASC
        """
        result = self.query(query, tuple(params))

        # 添加 source 字段
        for schedule in result:
            schedule['source'] = 'time_schedules'

        return result

    def update_schedule_status(self, schedule_id, status, user_id):
        """更新时间规划状态"""
        query = """
            UPDATE time_schedules
            SET status = %s, completed_at = IF(%s = 'completed', NOW(), NULL)
            WHERE id = %s AND user_id = %s
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, (status, status, schedule_id, user_id))
            return cursor.rowcount > 0

    def delete_schedule(self, schedule_id, user_id):
        """删除时间规划"""
        query = "DELETE FROM time_schedules WHERE id = %s AND user_id = %s"
        return self.execute(query, (schedule_id, user_id))
