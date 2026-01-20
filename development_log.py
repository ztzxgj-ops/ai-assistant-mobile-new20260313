#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发日志管理器
记录每次开发的需求、完成情况和备份时间
"""

import json
import os
from datetime import datetime
from pathlib import Path


class DevelopmentLogManager:
    """开发日志管理类"""

    def __init__(self, log_file='/Users/gj/编程/ai助理new/development_log.json'):
        self.log_file = log_file
        self.logs = []
        self.load_logs()

    def load_logs(self):
        """加载开发日志"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    self.logs = json.load(f)
            except Exception as e:
                print(f"加载开发日志失败: {e}")
                self.logs = []
        else:
            self.logs = []

    def save_logs(self):
        """保存开发日志"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存开发日志失败: {e}")

    def add_requirement(self, requirement, details=''):
        """添加开发需求

        Args:
            requirement: 需求描述
            details: 详细说明

        Returns:
            log_id: 日志ID
        """
        log_id = len(self.logs) + 1
        log_entry = {
            'id': log_id,
            'requirement': requirement,
            'details': details,
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'completion': None,  # 完成情况
            'completion_time': None,  # 完成时间
            'backup_time': None,  # 备份时间
            'status': 'in_progress'  # in_progress, completed, cancelled
        }
        self.logs.append(log_entry)
        self.save_logs()
        return log_id

    def update_completion(self, log_id, completion, status='completed'):
        """更新完成情况

        Args:
            log_id: 日志ID
            completion: 完成情况描述
            status: 状态 (completed, cancelled)
        """
        for log in self.logs:
            if log['id'] == log_id:
                log['completion'] = completion
                log['completion_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log['status'] = status
                self.save_logs()
                return True
        return False

    def mark_backup(self, log_id):
        """标记已备份

        Args:
            log_id: 日志ID
        """
        for log in self.logs:
            if log['id'] == log_id:
                log['backup_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.save_logs()
                return True
        return False

    def get_latest_log(self):
        """获取最新的日志条目"""
        if self.logs:
            return self.logs[-1]
        return None

    def get_recent_logs(self, limit=10):
        """获取最近的日志条目

        Args:
            limit: 返回数量
        """
        return self.logs[-limit:] if len(self.logs) > limit else self.logs

    def get_unbackuped_logs(self):
        """获取未备份的已完成日志"""
        return [log for log in self.logs
                if log['status'] == 'completed' and log['backup_time'] is None]

    def get_in_progress_logs(self):
        """获取进行中的日志"""
        return [log for log in self.logs if log['status'] == 'in_progress']

    def generate_backup_notes(self):
        """生成备份备注

        从未备份的已完成日志中生成备注
        """
        unbackuped = self.get_unbackuped_logs()

        if not unbackuped:
            # 如果没有未备份的完成记录，检查是否有进行中的
            in_progress = self.get_in_progress_logs()
            if in_progress:
                # 取最新的进行中任务
                latest = in_progress[-1]
                return f"🔧 开发中: {latest['requirement']}"
            return None

        # 生成备注：列出所有未备份的完成项
        if len(unbackuped) == 1:
            log = unbackuped[0]
            return f"✅ {log['requirement']}: {log['completion']}"
        else:
            # 多个完成项，列出前3个
            notes = "✅ 完成功能:\n"
            for i, log in enumerate(unbackuped[:3], 1):
                notes += f"{i}. {log['requirement']}: {log['completion']}\n"
            if len(unbackuped) > 3:
                notes += f"...还有 {len(unbackuped) - 3} 项"
            return notes.strip()

    def mark_all_as_backuped(self):
        """标记所有已完成但未备份的日志为已备份"""
        backup_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        count = 0
        for log in self.logs:
            if log['status'] == 'completed' and log['backup_time'] is None:
                log['backup_time'] = backup_time
                count += 1
        if count > 0:
            self.save_logs()
        return count

    def get_all_logs(self):
        """获取所有日志"""
        return self.logs

    def delete_log(self, log_id):
        """删除日志

        Args:
            log_id: 日志ID
        """
        self.logs = [log for log in self.logs if log['id'] != log_id]
        self.save_logs()
        return True


if __name__ == '__main__':
    # 测试代码
    manager = DevelopmentLogManager()

    # 添加需求
    log_id = manager.add_requirement(
        "修复完成命令功能",
        "修复'完成 1'命令在不同类别下的执行问题"
    )
    print(f"添加需求，ID: {log_id}")

    # 更新完成情况
    manager.update_completion(
        log_id,
        "已修复完成命令的数字提取逻辑，支持所有类别"
    )
    print("更新完成情况")

    # 生成备份备注
    notes = manager.generate_backup_notes()
    print(f"备份备注: {notes}")

    # 标记为已备份
    manager.mark_all_as_backuped()
    print("标记为已备份")

    # 查看所有日志
    print("\n所有日志:")
    for log in manager.get_all_logs():
        print(json.dumps(log, ensure_ascii=False, indent=2))
