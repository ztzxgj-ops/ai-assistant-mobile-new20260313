#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地备忘录同步脚本 - 从云服务器同步任务到本地Notes.app"""

import os
import sys
import json
import time
import requests
import subprocess
import re
from datetime import datetime

# 配置文件
CONFIG_FILE = "sync_config.json"
SYNC_STATE_FILE = "sync_notes_state.json"


class NotesSync:
    """本地备忘录同步器"""

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
            print("   请先创建配置文件")
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
            'synced_tasks': {},  # task_id -> note_title
            'last_sync': None
        }

    def _save_sync_state(self):
        """保存同步状态"""
        with open(SYNC_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.sync_state, f, ensure_ascii=False, indent=2)

    def login(self):
        """登录获取token"""
        if not self.username or not self.password:
            print("❌ 请先配置用户名和密码")
            print(f"   编辑 {CONFIG_FILE} 文件，填写 username 和 password")
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
                # API可能返回字典或列表
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

    def create_note(self, task):
        """在Notes.app中创建备忘录"""
        task_id = task['id']
        title = task['title']
        content = task.get('description', '')
        deadline = task.get('deadline', '')
        priority = task.get('priority', 'medium')

        # 格式化备忘录内容
        note_title, note_body = self._format_note(title, content, deadline, priority)

        # 使用AppleScript创建备忘录
        applescript = f'''
        tell application "Notes"
            make new note at folder "Notes" with properties {{name:"{self._escape(note_title)}", body:"{self._escape(note_body)}"}}
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
                print(f"✅ 创建备忘录: {title}")
                self.sync_state['synced_tasks'][str(task_id)] = note_title
                self._save_sync_state()
                return True
            else:
                print(f"❌ 创建备忘录失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 创建备忘录异常: {e}")
            return False

    def delete_note(self, task_id, note_title):
        """删除Notes.app中的备忘录"""
        applescript = f'''
        tell application "Notes"
            delete (every note whose name is "{self._escape(note_title)}")
        end tell
        '''

        try:
            subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=10
            )
            print(f"✅ 删除备忘录: {note_title}")
            del self.sync_state['synced_tasks'][str(task_id)]
            self._save_sync_state()
            return True
        except Exception as e:
            print(f"❌ 删除备忘录异常: {e}")
            return False

    def _format_note(self, title, content, deadline, priority):
        """格式化备忘录内容"""
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

        note_title = f"📋 {title}"

        lines = []
        if content:
            lines.append(content)
            lines.append("")

        if deadline:
            lines.append(f"⏰ 截止: {deadline}")

        lines.append(f"{emoji} 优先级: {priority_name}")

        note_body = "<br>".join(lines)

        return note_title, note_body

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

        # 当前服务器上的任务ID集合
        server_task_ids = set()
        pending_tasks = []

        for task in tasks:
            task_id = str(task['id'])
            status = task.get('status', 'pending')
            server_task_ids.add(task_id)

            # 只同步未完成的任务
            if status in ['pending', 'in_progress']:
                pending_tasks.append(task)

        # 1. 创建新任务的备忘录
        for task in pending_tasks:
            task_id = str(task['id'])
            if task_id not in self.sync_state['synced_tasks']:
                self.create_note(task)

        # 2. 删除已完成或已删除任务的备忘录
        synced_task_ids = list(self.sync_state['synced_tasks'].keys())
        for task_id in synced_task_ids:
            if task_id not in server_task_ids:
                # 任务已删除
                note_title = self.sync_state['synced_tasks'][task_id]
                self.delete_note(task_id, note_title)
            else:
                # 检查任务是否已完成
                task = next((t for t in tasks if str(t['id']) == task_id), None)
                if task and task.get('status') == 'completed':
                    note_title = self.sync_state['synced_tasks'][task_id]
                    self.delete_note(task_id, note_title)

        self.sync_state['last_sync'] = datetime.now().isoformat()
        self._save_sync_state()

        print(f"✅ 同步完成 - 当前跟踪 {len(self.sync_state['synced_tasks'])} 个任务")

    def run(self):
        """持续运行同步"""
        print("=" * 60)
        print("Mac备忘录同步服务")
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
    # 检查平台
    if sys.platform != 'darwin':
        print("❌ 此脚本仅支持macOS系统")
        return

    # 创建同步器
    syncer = NotesSync()

    # 运行同步
    syncer.run()


if __name__ == '__main__':
    main()
