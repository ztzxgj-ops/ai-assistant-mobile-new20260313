#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mac桌面便签管理器 - 使用Notes.app（备忘录）"""

import os
import sys
import subprocess
import re
from mysql_manager import MySQLManager


class StickyNoteManager:
    """Mac桌面便签管理器（简化版 - 只处理工作任务）

    使用macOS自带的Notes.app（备忘录）应用
    """

    def __init__(self, db_manager=None):
        """初始化便签管理器

        Args:
            db_manager: MySQL数据库管理器实例
        """
        self.db = db_manager if db_manager else MySQLManager()
        self.platform = sys.platform

        # 检查是否是macOS
        if self.platform != 'darwin':
            print("⚠️ 便签功能仅支持macOS系统")
            self.enabled = False
        else:
            self.enabled = True

    def create_work_task_note(self, task_id, title, content='', deadline='', priority='medium', user_id=None):
        """创建工作任务便签（使用Notes.app）

        Args:
            task_id: 工作任务ID
            title: 任务标题
            content: 任务内容描述
            deadline: 截止日期
            priority: 优先级 (low/medium/high/urgent)
            user_id: 用户ID

        Returns:
            bool: 是否成功
        """
        # 检查功能是否启用
        if not self.enabled:
            return False

        # 检查是否已存在便签
        if self._note_exists(task_id):
            print(f"⚠️ 任务 #{task_id} 已存在便签")
            return False

        try:
            # 格式化便签内容
            note_title, note_body = self._format_note_content(title, content, deadline, priority)

            # 使用AppleScript创建Notes备忘录
            applescript = f'''
            tell application "Notes"
                make new note at folder "Notes" with properties {{name:"{self._escape_applescript(note_title)}", body:"{self._escape_applescript(note_body)}"}}
            end tell
            '''

            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # 提取note ID
                note_id = self._extract_note_id(result.stdout)

                # 保存到数据库
                self._save_to_database(user_id, task_id, note_title, note_id)
                print(f"✅ 备忘录已创建: {title}")
                return True
            else:
                error_msg = result.stderr or '未知错误'
                print(f"❌ 备忘录创建失败: {error_msg}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ AppleScript执行超时")
            return False
        except Exception as e:
            print(f"❌ 创建备忘录异常: {e}")
            return False

    def delete_work_task_note(self, task_id):
        """删除工作任务备忘录

        通过note ID删除Notes.app中的备忘录

        Args:
            task_id: 工作任务ID

        Returns:
            bool: 是否成功
        """
        try:
            # 从数据库获取note_id
            sql = "SELECT id, note_title FROM sticky_notes WHERE task_id = %s"
            result = self.db.query(sql, (task_id,))

            if not result:
                print(f"⚠️ 未找到任务#{task_id}的备忘录记录")
                return False

            note_record = result[0]
            note_title = note_record.get('note_title', '')

            # 通过标题删除备忘录（因为AppleScript通过ID删除不可靠）
            applescript = f'''
            tell application "Notes"
                delete (every note whose name is "{self._escape_applescript(note_title)}")
            end tell
            '''

            subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=10
            )

            # 从数据库删除记录
            sql = "DELETE FROM sticky_notes WHERE task_id = %s"
            self.db.execute(sql, (task_id,))
            print(f"✅ 备忘录已删除: 任务#{task_id}")
            return True

        except Exception as e:
            print(f"❌ 删除备忘录失败: {e}")
            return False

    def _format_note_content(self, title, content, deadline, priority):
        """格式化备忘录内容

        Args:
            title: 标题
            content: 内容
            deadline: 截止日期
            priority: 优先级

        Returns:
            tuple: (note_title, note_body)
        """
        # 优先级emoji映射
        priority_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴',
            'urgent': '🔥'
        }

        priority_text = {
            'low': '低',
            'medium': '中',
            'high': '高',
            'urgent': '紧急'
        }

        emoji = priority_emoji.get(priority, '🟡')
        priority_name = priority_text.get(priority, '中')

        # 备忘录标题
        note_title = f"📋 {title}"

        # 备忘录正文
        lines = []

        if content:
            lines.append(content)
            lines.append("")

        if deadline:
            lines.append(f"⏰ 截止: {deadline}")

        lines.append(f"{emoji} 优先级: {priority_name}")

        note_body = "<br>".join(lines)  # Notes.app使用HTML格式

        return note_title, note_body

    def _escape_applescript(self, text):
        """转义AppleScript特殊字符

        Args:
            text: 原始文本

        Returns:
            str: 转义后的文本
        """
        if not text:
            return ""
        # 转义双引号和反斜杠
        text = text.replace('\\', '\\\\')
        text = text.replace('"', '\\"')
        return text

    def _extract_note_id(self, applescript_output):
        """从AppleScript输出中提取note ID

        Args:
            applescript_output: AppleScript的stdout输出

        Returns:
            str: note ID，如果提取失败返回None
        """
        # AppleScript返回格式: note id x-coredata://...
        match = re.search(r'note id (x-coredata://[^\s]+)', applescript_output)
        if match:
            return match.group(1)
        return None

    def _save_to_database(self, user_id, task_id, note_title, note_id=None):
        """保存备忘录记录到数据库

        Args:
            user_id: 用户ID
            task_id: 任务ID
            note_title: 备忘录标题
            note_id: 备忘录ID（可选）
        """
        sql = """
            INSERT INTO sticky_notes (user_id, task_id, note_title)
            VALUES (%s, %s, %s)
        """
        self.db.execute(sql, (user_id, task_id, note_title))

    def _note_exists(self, task_id):
        """检查任务是否已有便签

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否存在
        """
        sql = "SELECT id FROM sticky_notes WHERE task_id = %s"
        result = self.db.query(sql, (task_id,))
        return len(result) > 0


# 全局实例
_sticky_note_manager = None


def get_sticky_note_manager(db_manager=None):
    """获取全局便签管理器实例

    Args:
        db_manager: 数据库管理器实例

    Returns:
        StickyNoteManager: 便签管理器实例
    """
    global _sticky_note_manager
    if _sticky_note_manager is None:
        _sticky_note_manager = StickyNoteManager(db_manager)
    return _sticky_note_manager
