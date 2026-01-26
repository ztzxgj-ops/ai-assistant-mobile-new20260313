#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地备忘录同步脚本 - 汇总版（所有任务在一个备忘录中）"""

import os
import sys
import json
import time
import requests
import subprocess
from datetime import datetime

# 配置文件
CONFIG_FILE = "sync_config.json"
SYNC_STATE_FILE = "sync_notes_state.json"
NOTE_TITLE = "📋 工作任务清单"


class NotesSyncSummary:
    """本地备忘录同步器（汇总版）"""

    def __init__(self):
        self.config = self._load_config()
        self.server_url = self.config.get('server_url', 'http://47.109.148.176/ai/')
        self.username = self.config.get('username', '')
        self.password = self.config.get('password', '')
        self.sync_interval = self.config.get('sync_interval', 30)
        self.token = None
        self.sync_state = self._load_sync_state()

    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(CONFIG_FILE):
            print(f"❌ 配置文件不存在: {CONFIG_FILE}")
            sys.exit(1)

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            sys.exit(1)

    def _load_sync_state(self):
        """加载同步状态"""
        if os.path.exists(SYNC_STATE_FILE):
            try:
                with open(SYNC_STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'note_exists': False,
            'last_sync': None,
            'task_count': 0
        }

    def _save_sync_state(self):
        """保存同步状态"""
        with open(SYNC_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.sync_state, f, ensure_ascii=False, indent=2)

    def login(self):
        """登录获取token"""
        if not self.username or not self.password:
            print("❌ 请先配置用户名和密码")
            print(f"   编辑 {CONFIG_FILE} 文件")
            return False

        try:
            response = requests.post(
                f"{self.server_url}api/auth/login",
                json={"username": self.username, "password": self.password},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                print(f"✅ 登录成功")
                return True
            else:
                print(f"❌ 登录失败: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return False

    def get_tasks(self):
        """获取任务列表"""
        if not self.token:
            return None

        try:
            response = requests.get(
                f"{self.server_url}api/plans",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    return data.get('plans', [])
                elif isinstance(data, list):
                    return data
                else:
                    return []
            elif response.status_code == 401:
                print("⚠️ Token过期，重新登录...")
                if self.login():
                    return self.get_tasks()
            else:
                print(f"❌ 获取任务失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 获取任务异常: {e}")
            return None

    def create_or_update_summary_note(self, tasks):
        """创建或更新汇总备忘录"""
        # 格式化备忘录内容
        note_body = self._format_summary(tasks)

        # 检查备忘录是否已存在
        if self.sync_state.get('note_exists'):
            # 更新现有备忘录
            return self._update_note(note_body)
        else:
            # 创建新备忘录
            return self._create_note(note_body)

    def _create_note(self, note_body):
        """创建新备忘录"""
        applescript = f'''
        tell application "Notes"
            make new note at folder "Notes" with properties {{name:"{self._escape(NOTE_TITLE)}", body:"{self._escape(note_body)}"}}
        end tell
        '''

        try:
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(f"✅ 创建汇总备忘录")
                self.sync_state['note_exists'] = True
                self._save_sync_state()
                return True
            else:
                print(f"❌ 创建备忘录失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 创建备忘录异常: {e}")
            return False

    def _update_note(self, note_body):
        """更新现有备忘录"""
        # 先删除旧的，再创建新的（因为AppleScript更新内容比较复杂）
        applescript_delete = f'''
        tell application "Notes"
            delete (every note whose name is "{self._escape(NOTE_TITLE)}")
        end tell
        '''

        applescript_create = f'''
        tell application "Notes"
            make new note at folder "Notes" with properties {{name:"{self._escape(NOTE_TITLE)}", body:"{self._escape(note_body)}"}}
        end tell
        '''

        try:
            # 删除旧备忘录
            subprocess.run(['osascript', '-e', applescript_delete], capture_output=True, timeout=10)

            # 创建新备忘录
            result = subprocess.run(
                ['osascript', '-e', applescript_create],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(f"✅ 更新汇总备忘录")
                return True
            else:
                print(f"❌ 更新备忘录失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 更新备忘录异常: {e}")
            return False

    def _format_summary(self, tasks):
        """格式化汇总内容"""
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

        # 按优先级分组
        urgent_tasks = []
        high_tasks = []
        medium_tasks = []
        low_tasks = []

        for task in tasks:
            priority = task.get('priority', 'medium')
            if priority == 'urgent':
                urgent_tasks.append(task)
            elif priority == 'high':
                high_tasks.append(task)
            elif priority == 'medium':
                medium_tasks.append(task)
            else:
                low_tasks.append(task)

        # 构建内容
        lines = []
        lines.append(f"<b>更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</b>")
        lines.append(f"<b>任务总数：{len(tasks)}</b>")
        lines.append("<br>")

        # 紧急任务
        if urgent_tasks:
            lines.append("<b>🔥 紧急任务</b>")
            for i, task in enumerate(urgent_tasks, 1):
                title = task['title']
                deadline = task.get('deadline', '')
                lines.append(f"{i}. {title}")
                if deadline:
                    lines.append(f"   ⏰ {deadline}")
            lines.append("<br>")

        # 高优先级任务
        if high_tasks:
            lines.append("<b>🔴 高优先级</b>")
            for i, task in enumerate(high_tasks, 1):
                title = task['title']
                deadline = task.get('deadline', '')
                lines.append(f"{i}. {title}")
                if deadline:
                    lines.append(f"   ⏰ {deadline}")
            lines.append("<br>")

        # 中优先级任务
        if medium_tasks:
            lines.append("<b>🟡 中优先级</b>")
            for i, task in enumerate(medium_tasks, 1):
                title = task['title']
                deadline = task.get('deadline', '')
                lines.append(f"{i}. {title}")
                if deadline:
                    lines.append(f"   ⏰ {deadline}")
            lines.append("<br>")

        # 低优先级任务
        if low_tasks:
            lines.append("<b>🟢 低优先级</b>")
            for i, task in enumerate(low_tasks, 1):
                title = task['title']
                deadline = task.get('deadline', '')
                lines.append(f"{i}. {title}")
                if deadline:
                    lines.append(f"   ⏰ {deadline}")

        return "<br>".join(lines)

    def _escape(self, text):
        """转义AppleScript特殊字符"""
        if not text:
            return ""
        text = text.replace('\\', '\\\\')
        text = text.replace('"', '\\"')
        return text

    def sync_once(self):
        """执行一次同步"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始同步...")

        # 获取任务列表
        tasks = self.get_tasks()
        if tasks is None:
            print("⚠️ 获取任务失败，跳过本次同步")
            return

        # 只同步未完成的任务
        pending_tasks = [t for t in tasks if t.get('status') in ['pending', 'in_progress']]

        # 创建或更新汇总备忘录
        self.create_or_update_summary_note(pending_tasks)

        self.sync_state['last_sync'] = datetime.now().isoformat()
        self.sync_state['task_count'] = len(pending_tasks)
        self._save_sync_state()

        print(f"✅ 同步完成 - 当前 {len(pending_tasks)} 个任务")

    def run(self):
        """持续运行同步"""
        print("=" * 60)
        print("Mac备忘录同步服务（汇总版）")
        print("=" * 60)
        print(f"服务器: {self.server_url}")
        print(f"同步间隔: {self.sync_interval}秒")
        print("=" * 60)

        # 登录
        if not self.login():
            return

        print("\n🚀 同步服务已启动")
        print("按 Ctrl+C 停止\n")

        try:
            while True:
                self.sync_once()
                time.sleep(self.sync_interval)
        except KeyboardInterrupt:
            print("\n\n👋 同步服务已停止")
            self._save_sync_state()


def main():
    """主函数"""
    if sys.platform != 'darwin':
        print("❌ 此脚本仅支持macOS系统")
        return

    syncer = NotesSyncSummary()
    syncer.run()


if __name__ == '__main__':
    main()
