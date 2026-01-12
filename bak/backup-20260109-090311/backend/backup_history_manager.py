#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI助理系统备份历史管理器
管理备份历史记录、备注和恢复功能
"""

import json
import os
from datetime import datetime
from pathlib import Path


class BackupHistoryManager:
    """备份历史管理类"""

    def __init__(self, history_file='/Users/a1-6/Documents/GJ/编程/ai助理new/bak/backup_history.json'):
        self.history_file = history_file
        self.bak_dir = '/Users/a1-6/Documents/GJ/编程/ai助理new/bak'
        self.load_history()

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

        record = {
            'id': len(self.history) + 1,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'backup_dir': backup_dir,
            'status': status,
            'notes': notes,
            'error': error_msg,
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
