#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI助理系统备份历史管理器
管理备份历史记录、备注和恢复功能
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import mysql.connector


class BackupHistoryManager:
    """备份历史管理类"""

    def __init__(self, history_file='/Users/gj/编程/ai助理new/bak/backup_history.json'):
        self.history_file = history_file
        self.bak_dir = '/Users/gj/编程/ai助理new/bak'
        self.project_dir = '/Users/gj/编程/ai助理new'
        self.mysql_config_file = os.path.join(self.project_dir, 'mysql_config.json')
        self.load_history()
        self._load_mysql_config()

    def load_history(self):
        """加载备份历史"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except:
                self.history = []
        else:
            self.history = []

    def save_history(self):
        """保存备份历史"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def _load_mysql_config(self):
        """加载MySQL配置"""
        try:
            if os.path.exists(self.mysql_config_file):
                with open(self.mysql_config_file, 'r', encoding='utf-8') as f:
                    self.mysql_config = json.load(f)
            else:
                self.mysql_config = None
        except Exception as e:
            print(f"加载MySQL配置失败: {e}")
            self.mysql_config = None

    def _get_db_connection(self):
        """获取数据库连接"""
        if not self.mysql_config:
            return None
        try:
            return mysql.connector.connect(**self.mysql_config)
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return None

    def get_current_git_commit(self):
        """获取当前 git commit hash"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def get_uncommitted_changes(self):
        """获取未提交的修改文件列表"""
        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                modified_files = []
                for line in lines:
                    if line.strip():
                        # 格式: " M file.py" 或 "M  file.py" 或 "?? file.py"
                        parts = line.strip().split(None, 1)
                        if len(parts) == 2:
                            status, filename = parts
                            # 只关注修改和新增的文件，忽略删除和重命名
                            if status in ['M', 'MM', 'A', '??']:
                                # 排除备份目录和临时文件
                                if not filename.startswith('bak/') and not filename.endswith('.pyc'):
                                    modified_files.append(filename)
                return modified_files[:10]  # 最多返回10个文件
        except Exception:
            pass
        return []

    def get_recent_completed_tasks(self, hours=24):
        """获取最近完成的工作任务"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return []

            cursor = conn.cursor(dictionary=True)
            # 查询最近24小时内完成的任务
            query = """
                SELECT title, updated_at
                FROM work_plans
                WHERE status = 'completed'
                AND updated_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                ORDER BY updated_at DESC
                LIMIT 10
            """
            cursor.execute(query, (hours,))
            tasks = cursor.fetchall()
            cursor.close()
            conn.close()

            return [task['title'] for task in tasks]
        except Exception as e:
            print(f"查询工作任务失败: {e}")
            return []

    def get_recent_user_requests(self, hours=24):
        """从对话记录中提取用户需求"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return []

            cursor = conn.cursor(dictionary=True)
            # 查询最近的用户消息，寻找需求关键词
            query = """
                SELECT content, timestamp
                FROM messages
                WHERE role = 'user'
                AND timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                AND (
                    content LIKE '%希望%' OR content LIKE '%需要%'
                    OR content LIKE '%实现%' OR content LIKE '%修复%'
                    OR content LIKE '%添加%' OR content LIKE '%改进%'
                )
                ORDER BY timestamp DESC
                LIMIT 10
            """
            cursor.execute(query, (hours,))
            messages = cursor.fetchall()
            cursor.close()
            conn.close()

            # 提取简短的需求描述
            requests = []
            for msg in messages:
                content = msg['content'].strip()
                # 只取前50个字符作为摘要
                if len(content) > 50:
                    content = content[:50] + '...'
                requests.append(content)

            return requests
        except Exception as e:
            print(f"查询对话记录失败: {e}")
            return []

    def generate_git_notes(self):
        """根据上次备份后的 git 变更自动生成备注"""
        try:
            # 获取当前 commit
            current_commit = self.get_current_git_commit()
            if not current_commit:
                return "备份类型: 标准备份"

            # 获取上次备份的 commit
            last_commit = None
            if self.history and len(self.history) > 0:
                last_commit = self.history[0].get('git_commit')

            # 如果没有上次备份的 commit，使用最近 5 条提交
            if not last_commit:
                result = subprocess.run(
                    ['git', 'log', '--oneline', '-5', '--no-decorate'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    commits = result.stdout.strip().split('\n')
                    # 只取前3条，去掉 commit hash
                    commit_msgs = []
                    for commit in commits[:3]:
                        parts = commit.split(' ', 1)
                        if len(parts) > 1:
                            commit_msgs.append(parts[1])
                    if commit_msgs:
                        return "最近变更: " + "; ".join(commit_msgs)
                return "备份类型: 标准备份"

            # 获取两次备份之间的提交记录
            result = subprocess.run(
                ['git', 'log', f'{last_commit}..HEAD', '--oneline', '--no-decorate'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

            commit_msgs = []
            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().split('\n')
                # 只取前5条，去掉 commit hash
                for commit in commits[:5]:
                    parts = commit.split(' ', 1)
                    if len(parts) > 1:
                        commit_msgs.append(parts[1])

            # 检查未提交的修改
            uncommitted = self.get_uncommitted_changes()

            # 生成备注
            if commit_msgs:
                # 如果只有1-2条提交，直接显示
                if len(commit_msgs) <= 2:
                    notes = "变更: " + "; ".join(commit_msgs)
                # 如果有多条，显示前3条
                else:
                    notes = "变更: " + "; ".join(commit_msgs[:3])
                    if len(commits) > 3:
                        notes += f" (共{len(commits)}个提交)"

                # 如果还有未提交的修改，追加提示
                if uncommitted:
                    notes += " + 有未提交的代码修改"
                return notes
            elif uncommitted:
                # 没有新提交，但有未提交的修改
                # 优先显示最近的 git commit 作为上下文
                result = subprocess.run(
                    ['git', 'log', '--oneline', '-3', '--no-decorate'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0 and result.stdout.strip():
                    commits = result.stdout.strip().split('\n')
                    commit_msgs = []
                    for commit in commits[:2]:  # 取最近2条
                        parts = commit.split(' ', 1)
                        if len(parts) > 1:
                            commit_msgs.append(parts[1])

                    if commit_msgs:
                        # 显示最近的 commit 作为上下文
                        base_note = "最近更新: " + "; ".join(commit_msgs)
                        # 追加修改文件数量提示
                        if len(uncommitted) <= 3:
                            base_note += f"\n📝 当前修改: {', '.join(uncommitted)}"
                        else:
                            base_note += f"\n📝 当前修改: {len(uncommitted)}个文件"
                        return base_note

                # 如果获取 commit 失败，只显示修改的文件
                if len(uncommitted) == 1:
                    return f"📝 代码修改: {uncommitted[0]}"
                elif len(uncommitted) <= 5:
                    return "📝 代码修改:\n  • " + "\n  • ".join(uncommitted)
                else:
                    return f"📝 代码修改: {', '.join(uncommitted[:3])} 等 {len(uncommitted)} 个文件"
            else:
                return "无新提交"

        except Exception as e:
            print(f"生成 git 备注失败: {e}")
            return "备份类型: 标准备份"

    def add_backup_record(self, backup_dir, status='success', notes='', error_msg=''):
        """添加备份记录"""
        # 获取备份文件信息
        backup_path = os.path.join(self.bak_dir, backup_dir)
        code_file = None
        db_file = None
        code_size = 0
        db_size = 0

        if os.path.isdir(backup_path):
            for f in os.listdir(backup_path):
                if f.startswith('ai-assistant-backup-') and f.endswith('.tar.gz'):
                    code_file = f
                    code_size = os.path.getsize(os.path.join(backup_path, f))
                elif f.startswith('ai_assistant_db_backup') and f.endswith('.sql'):
                    db_file = f
                    db_size = os.path.getsize(os.path.join(backup_path, f))

        # 获取当前 git commit
        git_commit = self.get_current_git_commit()

        record = {
            'id': len(self.history) + 1,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'backup_dir': backup_dir,
            'status': status,
            'notes': notes,
            'error': error_msg,
            'git_commit': git_commit,  # 添加 git commit hash
            'files': {
                'code': {
                    'name': code_file,
                    'size': code_size
                },
                'database': {
                    'name': db_file,
                    'size': db_size
                }
            }
        }

        self.history.insert(0, record)  # 新记录在最前面
        self.save_history()
        return record

    def update_backup_record(self, backup_id, notes='', status=None):
        """更新备份记录备注"""
        for record in self.history:
            if record['id'] == backup_id:
                if notes:
                    record['notes'] = notes
                if status:
                    record['status'] = status
                self.save_history()
                return record
        return None

    def get_history(self, limit=20):
        """获取备份历史（最近N条）"""
        return self.history[:limit]

    def get_record_by_dir(self, backup_dir):
        """根据备份目录获取记录"""
        for record in self.history:
            if record['backup_dir'] == backup_dir:
                return record
        return None

    def format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"

    def get_history_display(self):
        """获取格式化的历史记录用于显示"""
        result = []
        for record in self.history:
            result.append({
                'id': record['id'],
                'timestamp': record['timestamp'],
                'backup_dir': record['backup_dir'],
                'status': record['status'],
                'notes': record['notes'],
                'code_size': self.format_size(record['files']['code']['size']),
                'db_size': self.format_size(record['files']['database']['size']),
                'code_file': record['files']['code']['name'],
                'db_file': record['files']['database']['name'],
            })
        return result


if __name__ == '__main__':
    manager = BackupHistoryManager()

    # 示例：添加记录
    # record = manager.add_backup_record('backup-20260108-151424', 'success', '修复缓存文件排除')
    # print("添加记录:", record)

    # 获取历史
    history = manager.get_history_display()
    for item in history[:5]:
        print(json.dumps(item, ensure_ascii=False, indent=2))
