#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os
from datetime import datetime
from typing import List, Dict

class ChatMemory:
    def __init__(self, storage_file='chat_memory.json'):
        self.storage_file = storage_file
        self.conversations = []
        self.load_memory()
    
    def add_message(self, role: str, content: str, tags: List[str] = None, user_id: int = None):
        self.conversations.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'role': role, 'content': content, 'tags': tags or [],
            'user_id': user_id
        })
        self.save_memory()

    def search_by_keyword(self, keyword: str, user_id: int = None) -> List[Dict]:
        results = [m for m in self.conversations if keyword.lower() in m['content'].lower()]
        if user_id is not None:
            results = [m for m in results if m.get('user_id') == user_id]
        return results

    def get_recent_conversations(self, count: int = 10, user_id: int = None) -> List[Dict]:
        conversations = self.conversations
        if user_id is not None:
            conversations = [m for m in conversations if m.get('user_id') == user_id]
        return conversations[-count:]
    
    def save_memory(self):
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(self.conversations, f, ensure_ascii=False, indent=2)
    
    def load_memory(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self.conversations = json.load(f)
            except: self.conversations = []

class WorkPlan:
    def __init__(self, storage_file='work_plans.json'):
        self.storage_file = storage_file
        self.plans = []
        self.load_plans()
    
    def add_plan(self, title, description, deadline, priority='中', status='未开始', user_id=None):
        plan = {'id': len(self.plans) + 1, 'title': title, 'description': description,
                'deadline': deadline, 'priority': priority, 'status': status,
                'user_id': user_id,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        self.plans.append(plan)
        self.save_plans()
        return plan

    def update_plan(self, plan_id, user_id=None, **kwargs):
        for p in self.plans:
            if p['id'] == plan_id:
                # 如果提供了user_id，验证权限
                if user_id is not None and p.get('user_id') != user_id:
                    return False  # 权限不足
                p.update(kwargs)
                self.save_plans()
                return True
        return False

    def delete_plan(self, plan_id, user_id=None):
        # 如果提供了user_id，验证权限
        if user_id is not None:
            plan = next((p for p in self.plans if p['id'] == plan_id), None)
            if plan and plan.get('user_id') != user_id:
                return False  # 权限不足
        self.plans = [p for p in self.plans if p['id'] != plan_id]
        self.save_plans()
        return True

    def list_plans(self, status=None, user_id=None):
        plans = self.plans
        if user_id is not None:
            plans = [p for p in plans if p.get('user_id') == user_id]
        if status:
            plans = [p for p in plans if p['status'] == status]
        return plans
    
    def save_plans(self):
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(self.plans, f, ensure_ascii=False, indent=2)
    
    def load_plans(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self.plans = json.load(f)
            except: self.plans = []

class ReminderSystem:
    def __init__(self, storage_file='reminders.json'):
        self.storage_file = storage_file
        self.reminders = []
        self.running = False
        self.load_reminders()
    
    def start_monitoring(self): self.running = True
    def stop_monitoring(self): self.running = False
    
    def add_reminder(self, title, message, remind_time, repeat='不重复', sound='Ping', user_id=None):
        reminder = {'id': len(self.reminders) + 1, 'title': title, 'message': message,
                   'remind_time': remind_time, 'repeat': repeat, 'sound': sound,
                   'status': '活跃', 'user_id': user_id,
                   'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        self.reminders.append(reminder)
        self.save_reminders()
        return reminder
    
    def delete_reminder(self, reminder_id, user_id=None):
        # 如果提供了user_id，验证权限
        if user_id is not None:
            reminder = next((r for r in self.reminders if r['id'] == reminder_id), None)
            if reminder and reminder.get('user_id') != user_id:
                return False  # 权限不足
        self.reminders = [r for r in self.reminders if r['id'] != reminder_id]
        self.save_reminders()
        return True
    
    def list_reminders(self, status=None, user_id=None):
        reminders = self.reminders
        if user_id is not None:
            reminders = [r for r in reminders if r.get('user_id') == user_id]
        if status:
            reminders = [r for r in reminders if r['status'] == status]
        return reminders
    
    def save_reminders(self):
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(self.reminders, f, ensure_ascii=False, indent=2)
    
    def load_reminders(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self.reminders = json.load(f)
            except: self.reminders = []
