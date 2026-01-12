#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""个人助手 - Web版本（优化版）"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import webbrowser
import threading
from datetime import datetime, timedelta
from personal_assistant import ChatMemory, WorkPlan, ReminderSystem
from ai_chat_assistant import AIAssistant

# 全局数据管理器
memory = ChatMemory('web_chat_memory.json')
planner = WorkPlan('web_work_plans.json')
reminder_sys = ReminderSystem('web_reminders.json')
ai_assistant = AIAssistant()

class AssistantHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/' or self.path == '/index.html':
            self.send_html()
        elif self.path == '/api/chats':
            self.send_json(memory.conversations)
        elif self.path == '/api/plans':
            self.send_json(planner.plans)
        elif self.path == '/api/reminders':
            self.send_json(reminder_sys.reminders)
        elif self.path == '/api/ai/get_mode':
            self.send_json({'mode': ai_assistant.model_type, 'config': ai_assistant.config})
        else:
            self.send_error(404)
    
    def do_POST(self):
        """处理POST请求"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(post_data)
        
        if self.path == '/api/ai/chat':
            response_text = ai_assistant.chat(data.get('message', ''))
            self.send_json({'response': response_text})
        
        elif self.path == '/api/ai/clear':
            ai_assistant.clear_conversation()
            self.send_json({'success': True, 'message': '对话已清空'})
        
        elif self.path == '/api/ai/switch_mode':
            mode = data.get('mode', 'simple')
            ai_assistant.config['model_type'] = mode
            ai_assistant.model_type = mode
            # 保存到配置文件
            with open('ai_config.json', 'w', encoding='utf-8') as f:
                json.dump(ai_assistant.config, f, ensure_ascii=False, indent=2)
            self.send_json({'success': True, 'mode': mode, 'message': f'已切换到{mode}模式'})
        
        elif self.path == '/api/chat/add':
            memory.add_message(
                data.get('role', 'user'),
                data.get('content', ''),
                data.get('tags', [])
            )
            self.send_json({'success': True, 'message': '记录已添加'})
        
        elif self.path == '/api/plan/add':
            planner.add_plan(
                data.get('title', ''),
                data.get('description', ''),
                data.get('deadline', ''),
                data.get('priority', '中'),
                data.get('status', '未开始')
            )
            self.send_json({'success': True, 'message': '计划已添加'})
        
        elif self.path == '/api/plan/update':
            planner.update_plan(data.get('id'), status=data.get('status'))
            self.send_json({'success': True, 'message': '计划已更新'})
        
        elif self.path == '/api/plan/delete':
            planner.delete_plan(data.get('id'))
            self.send_json({'success': True, 'message': '计划已删除'})
        
        elif self.path == '/api/reminder/add':
            reminder_sys.add_reminder(
                data.get('title', ''),
                data.get('message', ''),
                data.get('remind_time', ''),
                data.get('repeat', '不重复'),
                data.get('sound', 'Ping')
            )
            self.send_json({'success': True, 'message': '提醒已添加'})
        
        elif self.path == '/api/reminder/delete':
            reminder_sys.delete_reminder(data.get('id'))
            self.send_json({'success': True, 'message': '提醒已删除'})
        
        elif self.path == '/api/chat/create_reminder':
            reminder_sys.add_reminder(
                data.get('title', '聊天提醒'),
                data.get('content', ''),
                data.get('remind_time', ''),
                data.get('repeat', '不重复'),
                data.get('sound', 'Ping')
            )
            self.send_json({'success': True, 'message': '提醒已创建'})
        
        else:
            self.send_error(404)
    
    def send_json(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_html(self):
        """发送HTML页面"""
        html_content = self.get_html_template()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def get_html_template(self):
        """获取HTML模板"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>个人助手</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f7fa;
            min-height: 100vh;
        }
        
        .app-header {
            background: white;
            border-bottom: 1px solid #e8eaed;
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .logo {
            font-size: 20px;
            font-weight: 600;
            color: #1a73e8;
        }
        
        .container {
            max-width: 1200px;
            margin: 24px auto;
            padding: 0 24px;
        }
        .tabs {
            display: flex;
            background: #f8f9fa;
        }
        .tab {
            flex: 1;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            background: #f8f9fa;
            border: none;
            font-size: 1.1em;
            transition: all 0.3s;
        }
        .tab:hover { background: #e9ecef; }
        .tab.active {
            background: white;
            border-bottom: 3px solid #667eea;
            font-weight: bold;
        }
        .tab-content { display: none; padding: 30px; }
        .tab-content.active { display: block; }
        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #495057;
        }
        input[type="text"], select, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            font-size: 1em;
        }
        textarea { resize: vertical; min-height: 80px; }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
        }
        button:hover { transform: translateY(-2px); }
        .card {
            background: #f8f9fa;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            margin-right: 5px;
            color: white;
        }
        .list-container { max-height: 500px; overflow-y: auto; }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        .modal-content {
            background-color: white;
            margin: 10% auto;
            padding: 30px;
            border-radius: 15px;
            width: 90%;
            max-width: 500px;
        }
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 个人助手系统</h1>
            <p>AI对话 · 聊天记忆 · 工作计划 · 定时提醒</p>
        </header>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab(event, 'ai')">🤖 AI助手</button>
            <button class="tab" onclick="showTab(event, 'chat')">📝 聊天记忆</button>
            <button class="tab" onclick="showTab(event, 'plan')">📅 工作计划</button>
            <button class="tab" onclick="showTab(event, 'reminder')">⏰ 定时提醒</button>
        </div>
        
        <!-- AI助手 -->
        <div id="ai" class="tab-content active">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h2 style="margin: 0;">🤖 AI智能助手</h2>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <select id="aiModeSelect" onchange="switchAIMode()" style="padding: 8px 15px; border-radius: 8px; border: 2px solid #667eea; background: white; font-size: 0.9em; cursor: pointer;">
                        <option value="simple" selected>⚡ 简单模式（快速）</option>
                        <option value="ollama">🤖 智能模式（AI）</option>
                    </select>
                    <button onclick="clearConversation()" style="padding: 8px 20px; background: #ff6b6b; font-size: 0.9em;">🆕 新对话</button>
                </div>
            </div>
            <div id="modeIndicator" style="padding: 10px; margin-bottom: 10px; border-radius: 8px; background: #e3f2fd; color: #1976d2; font-size: 0.9em; text-align: center;">
                ⚡ 当前模式：<b>简单模式</b> - 瞬间响应，不发热
            </div>
            <div id="aiChatBox" class="list-container" style="background: #f8f9fa; padding: 20px; border-radius: 10px; min-height: 400px;">
                <div style="text-align: center; padding: 40px; color: #adb5bd;">
                    <h3>👋 你好！问我任何问题</h3>
                    <p>我可以帮你查询聊天记录、工作计划和提醒</p>
                    <p style="font-size: 0.9em; margin-top: 10px;">💡 我会记住对话上下文，可以连续提问</p>
                </div>
            </div>
            <div class="form-group" style="margin-top: 20px;">
                <textarea id="aiInput" rows="2" placeholder="例如：我说过公积金的内容吗？（按Enter发送，Shift+Enter换行）" onkeydown="handleAIKeyPress(event)"></textarea>
                <button onclick="sendAI()" style="margin-top:10px">发送 (Enter)</button>
            </div>
        </div>
        
        <!-- 聊天记忆 -->
        <div id="chat" class="tab-content">
            <h2>添加聊天记录</h2>
            <div class="form-group">
                <label>角色</label>
                <select id="chatRole">
                    <option value="user">用户</option>
                    <option value="assistant">助手</option>
                </select>
            </div>
            <div class="form-group">
                <label>内容</label>
                <textarea id="chatContent"></textarea>
            </div>
            <div class="form-group">
                <label>标签（逗号分隔）</label>
                <input type="text" id="chatTags">
            </div>
            <button onclick="addChat()">添加记录</button>
            <button onclick="loadChats()" style="margin-left:10px;background:#48dbfb">刷新</button>
            <div id="chatList" class="list-container" style="margin-top:20px"></div>
        </div>
        
        <!-- 工作计划 -->
        <div id="plan" class="tab-content">
            <h2>添加工作计划</h2>
            <div class="form-group">
                <label>标题</label>
                <input type="text" id="planTitle">
            </div>
            <div class="form-group">
                <label>描述</label>
                <textarea id="planDesc"></textarea>
            </div>
            <div class="form-group">
                <label>截止时间</label>
                <input type="text" id="planDeadline" placeholder="YYYY-MM-DD HH:MM">
            </div>
            <div class="form-group">
                <label>优先级</label>
                <select id="planPriority">
                    <option value="高">高</option>
                    <option value="中" selected>中</option>
                    <option value="低">低</option>
                </select>
            </div>
            <button onclick="addPlan()">添加计划</button>
            <button onclick="loadPlans()" style="margin-left:10px;background:#48dbfb">刷新</button>
            <div id="planList" class="list-container" style="margin-top:20px"></div>
        </div>
        
        <!-- 定时提醒 -->
        <div id="reminder" class="tab-content">
            <h2>添加定时提醒</h2>
            <div class="form-group">
                <label>标题</label>
                <input type="text" id="reminderTitle">
            </div>
            <div class="form-group">
                <label>内容</label>
                <textarea id="reminderMessage"></textarea>
            </div>
            <div class="form-group">
                <label>提醒时间</label>
                <input type="text" id="reminderTime" placeholder="YYYY-MM-DD HH:MM">
            </div>
            <div class="form-group">
                <label>重复</label>
                <select id="reminderRepeat">
                    <option value="不重复" selected>不重复</option>
                    <option value="每天">每天</option>
                    <option value="每周">每周</option>
                    <option value="每月">每月</option>
                </select>
            </div>
            <div class="form-group">
                <label>🎵 提示音</label>
                <select id="reminderSound">
                    <option value="Ping" selected>⭐⭐⭐⭐⭐ Ping - 最清脆</option>
                    <option value="Glass">⭐⭐⭐⭐ Glass - 玻璃声</option>
                    <option value="Bottle">⭐⭐⭐⭐ Bottle - 瓶子声</option>
                    <option value="Pop">⭐⭐⭐ Pop - 气泡声</option>
                    <option value="Tink">⭐⭐⭐ Tink - 金属声</option>
                </select>
            </div>
            <button onclick="addReminder()">添加提醒</button>
            <button onclick="loadReminders()" style="margin-left:10px;background:#48dbfb">刷新</button>
            <div id="reminderList" class="list-container" style="margin-top:20px"></div>
        </div>
    </div>
    
    <!-- 弹窗 -->
    <div id="reminderModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h3>⏰ 设置提醒</h3>
            <div class="form-group">
                <label>标题</label>
                <input type="text" id="modalTitle">
            </div>
            <div class="form-group">
                <label>内容</label>
                <textarea id="modalContent" readonly></textarea>
            </div>
            <div class="form-group">
                <label>时间</label>
                <input type="text" id="modalTime">
            </div>
            <div class="form-group">
                <label>重复</label>
                <select id="modalRepeat">
                    <option value="不重复">不重复</option>
                    <option value="每天">每天</option>
                </select>
            </div>
            <div class="form-group">
                <label>🎵 提示音</label>
                <select id="modalSound">
                    <option value="Ping" selected>Ping - 最清脆</option>
                    <option value="Glass">Glass - 玻璃声</option>
                    <option value="Bottle">Bottle - 瓶子声</option>
                </select>
            </div>
            <button onclick="createReminder()">创建</button>
        </div>
    </div>
    
    <script>
        function showTab(evt, tabName) {
            const tabs = document.querySelectorAll('.tab');
            const contents = document.querySelectorAll('.tab-content');
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));
            evt.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }
        
        // AI助手 - 处理回车键
        function handleAIKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendAI();
            }
        }
        
        // AI助手
        async function sendAI() {
            const input = document.getElementById('aiInput');
            const msg = input.value.trim();
            if (!msg) return;
            
            appendAI('user', msg);
            input.value = '';
            
            const box = document.getElementById('aiChatBox');
            if (box.querySelector('h3')) box.innerHTML = '';
            
            const loading = document.createElement('div');
            loading.id = 'loading';
            loading.style.cssText = 'padding:15px;text-align:center;color:#6c757d';
            loading.textContent = '🤔 思考中...';
            box.appendChild(loading);
            
            try {
                const res = await fetch('/api/ai/chat', {
                    method: 'POST',
                    body: JSON.stringify({message: msg})
                });
                const data = await res.json();
                document.getElementById('loading')?.remove();
                appendAI('ai', data.response);
            } catch(e) {
                document.getElementById('loading')?.remove();
                appendAI('ai', '出错了：' + e);
            }
        }
        
        function appendAI(role, text) {
            const box = document.getElementById('aiChatBox');
            const div = document.createElement('div');
            div.style.cssText = role === 'user' 
                ? 'padding:15px;margin:10px 0 10px 50px;border-radius:10px;background:linear-gradient(135deg,#667eea,#764ba2);color:white'
                : 'padding:15px;margin:10px 50px 10px 0;border-radius:10px;background:white;border:2px solid #e9ecef';
            div.innerHTML = `<b>${role === 'user' ? '👤 你' : '🤖 AI'}</b><br><div style="margin-top:8px;white-space:pre-wrap">${text}</div>`;
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }
        
        async function clearConversation() {
            if (!confirm('确定要开始新对话吗？当前对话历史将被清空。')) return;
            
            try {
                await fetch('/api/ai/clear', {
                    method: 'POST',
                    body: JSON.stringify({})
                });
                
                const box = document.getElementById('aiChatBox');
                box.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #adb5bd;">
                        <h3>✨ 新对话已开始</h3>
                        <p>我已忘记之前的对话内容，让我们重新开始吧！</p>
                        <p style="font-size: 0.9em; margin-top: 10px;">💡 我会记住本次对话的上下文</p>
                    </div>
                `;
                
                alert('✅ 新对话已开始！');
            } catch(e) {
                alert('操作失败：' + e);
            }
        }
        
        async function switchAIMode() {
            const select = document.getElementById('aiModeSelect');
            const mode = select.value;
            const indicator = document.getElementById('modeIndicator');
            
            try {
                const resp = await fetch('/api/ai/switch_mode', {
                    method: 'POST',
                    body: JSON.stringify({mode: mode})
                });
                
                const data = await resp.json();
                
                if (data.success) {
                    if (mode === 'simple') {
                        indicator.style.background = '#e3f2fd';
                        indicator.style.color = '#1976d2';
                        indicator.innerHTML = '⚡ 当前模式：<b>简单模式</b> - 瞬间响应，不发热';
                    } else {
                        indicator.style.background = '#f3e5f5';
                        indicator.style.color = '#7b1fa2';
                        indicator.innerHTML = '🤖 当前模式：<b>智能模式</b> - AI理解，需要5-15秒';
                    }
                    
                    // 清空对话框提示用户
                    const box = document.getElementById('aiChatBox');
                    box.innerHTML = `
                        <div style="text-align: center; padding: 40px; color: #adb5bd;">
                            <h3>🔄 已切换到${mode === 'simple' ? '简单' : '智能'}模式</h3>
                            <p>${mode === 'simple' ? '⚡ 快速搜索，瞬间响应' : '🤖 AI智能理解，耐心等待'}</p>
                        </div>
                    `;
                }
            } catch(e) {
                alert('切换失败：' + e);
            }
        }
        
        // 聊天记忆
        async function addChat() {
            const role = document.getElementById('chatRole').value;
            const content = document.getElementById('chatContent').value.trim();
            const tags = document.getElementById('chatTags').value.trim().split(',').map(t => t.trim()).filter(t => t);
            
            if (!content) { alert('请输入内容'); return; }
            
            await fetch('/api/chat/add', {
                method: 'POST',
                body: JSON.stringify({role, content, tags})
            });
            
            alert('已添加');
            document.getElementById('chatContent').value = '';
            document.getElementById('chatTags').value = '';
            loadChats();
        }
        
        async function loadChats() {
            const res = await fetch('/api/chats');
            const chats = await res.json();
            const list = document.getElementById('chatList');
            
            list.innerHTML = chats.slice().reverse().map(c => `
                <div class="card">
                    <div><b>[${c.timestamp}] ${c.role}</b></div>
                    <div style="margin-top:10px">${c.content}</div>
                    ${c.tags?.length ? '<div style="margin-top:10px">' + c.tags.map(t => 
                        `<span class="badge" style="background:#667eea">${t}</span>`
                    ).join('') + '</div>' : ''}
                    <button onclick='openModal(${JSON.stringify(c)})' style="margin-top:10px;padding:6px 15px;font-size:0.9em;background:#fa709a">⏰ 设置提醒</button>
                </div>
            `).join('');
        }
        
        // 工作计划
        async function addPlan() {
            const title = document.getElementById('planTitle').value.trim();
            const description = document.getElementById('planDesc').value.trim();
            const deadline = document.getElementById('planDeadline').value.trim();
            const priority = document.getElementById('planPriority').value;
            
            if (!title) { alert('请输入标题'); return; }
            
            await fetch('/api/plan/add', {
                method: 'POST',
                body: JSON.stringify({title, description, deadline, priority})
            });
            
            alert('已添加');
            document.getElementById('planTitle').value = '';
            document.getElementById('planDesc').value = '';
            loadPlans();
        }
        
        async function loadPlans() {
            const res = await fetch('/api/plans');
            const plans = await res.json();
            const list = document.getElementById('planList');
            
            list.innerHTML = plans.map(p => `
                <div class="card">
                    <div><b>${p.title}</b>
                        <span class="badge" style="background:${p.priority==='高'?'#f5576c':p.priority==='中'?'#feca57':'#48dbfb'}">${p.priority}</span>
                        <span class="badge" style="background:${p.status==='已完成'?'#1dd1a1':'#feca57'}">${p.status}</span>
                    </div>
                    <div style="margin-top:10px">${p.description}</div>
                    <div style="margin-top:10px"><b>截止:</b> ${p.deadline}</div>
                    ${p.status !== '已完成' ? `
                        <button onclick="completePlan(${p.id})" style="margin-top:10px;padding:6px 15px;font-size:0.9em">完成</button>
                        <button onclick="deletePlan(${p.id})" style="margin-top:10px;padding:6px 15px;font-size:0.9em;background:#f5576c">删除</button>
                    ` : ''}
                </div>
            `).join('');
        }
        
        async function completePlan(id) {
            await fetch('/api/plan/update', {
                method: 'POST',
                body: JSON.stringify({id, status: '已完成'})
            });
            loadPlans();
        }
        
        async function deletePlan(id) {
            if (!confirm('确定删除?')) return;
            await fetch('/api/plan/delete', {
                method: 'POST',
                body: JSON.stringify({id})
            });
            loadPlans();
        }
        
        // 提醒
        async function addReminder() {
            const title = document.getElementById('reminderTitle').value.trim();
            const message = document.getElementById('reminderMessage').value.trim();
            const remind_time = document.getElementById('reminderTime').value.trim();
            const repeat = document.getElementById('reminderRepeat').value;
            const sound = document.getElementById('reminderSound').value;
            
            if (!title) { alert('请输入标题'); return; }
            
            await fetch('/api/reminder/add', {
                method: 'POST',
                body: JSON.stringify({title, message, remind_time, repeat, sound})
            });
            
            alert('已添加');
            document.getElementById('reminderTitle').value = '';
            document.getElementById('reminderMessage').value = '';
            loadReminders();
        }
        
        async function loadReminders() {
            const res = await fetch('/api/reminders');
            const reminders = await res.json();
            const list = document.getElementById('reminderList');
            
            list.innerHTML = reminders.map(r => `
                <div class="card">
                    <div><b>${r.title}</b>
                        <span class="badge" style="background:#48dbfb">${r.repeat}</span>
                        <span class="badge" style="background:#fa709a">🎵 ${r.sound || 'Ping'}</span>
                    </div>
                    <div style="margin-top:10px">${r.message}</div>
                    <div style="margin-top:10px"><b>时间:</b> ${r.remind_time}</div>
                    <button onclick="deleteReminder(${r.id})" style="margin-top:10px;padding:6px 15px;font-size:0.9em;background:#f5576c">删除</button>
                </div>
            `).join('');
        }
        
        async function deleteReminder(id) {
            if (!confirm('确定删除?')) return;
            await fetch('/api/reminder/delete', {
                method: 'POST',
                body: JSON.stringify({id})
            });
            loadReminders();
        }
        
        // 弹窗
        function openModal(chat) {
            document.getElementById('modalTitle').value = '关于：' + chat.content.substring(0, 20);
            document.getElementById('modalContent').value = chat.content;
            const now = new Date();
            now.setHours(now.getHours() + 1);
            document.getElementById('modalTime').value = now.toISOString().slice(0,16).replace('T', ' ');
            document.getElementById('reminderModal').style.display = 'block';
        }
        
        function closeModal() {
            document.getElementById('reminderModal').style.display = 'none';
        }
        
        async function createReminder() {
            const title = document.getElementById('modalTitle').value;
            const content = document.getElementById('modalContent').value;
            const time = document.getElementById('modalTime').value;
            const repeat = document.getElementById('modalRepeat').value;
            const sound = document.getElementById('modalSound').value;
            
            await fetch('/api/chat/create_reminder', {
                method: 'POST',
                body: JSON.stringify({title, content, remind_time: time, repeat, sound})
            });
            
            alert('提醒已创建');
            closeModal();
            loadReminders();
            document.querySelectorAll('.tab')[3].click();
        }
        
        window.onload = () => {
            loadChats();
            loadPlans();
            loadReminders();
            
            // 加载当前AI模式
            fetch('/api/ai/get_mode')
                .then(r => r.json())
                .then(data => {
                    const select = document.getElementById('aiModeSelect');
                    const indicator = document.getElementById('modeIndicator');
                    select.value = data.mode || 'simple';
                    
                    if (data.mode === 'ollama') {
                        indicator.style.background = '#f3e5f5';
                        indicator.style.color = '#7b1fa2';
                        indicator.innerHTML = '🤖 当前模式：<b>智能模式</b> - AI理解，需要5-15秒';
                    }
                })
                .catch(e => console.log('加载模式失败', e));
        };
    </script>
</body>
</html>'''
    
    def log_message(self, format, *args):
        """日志"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format%args}")

def run_server(port=8000):
    """运行服务器"""
    reminder_sys.start_monitoring()
    
    server = HTTPServer(('', port), AssistantHandler)
    
    print(f"\n{'='*60}")
    print(f"🤖 个人助手系统 - Web版")
    print(f"{'='*60}")
    print(f"\n✅ 服务器已启动: http://localhost:{port}")
    print(f"\n💡 按 Ctrl+C 停止")
    print(f"{'='*60}\n")
    
    threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{port}')).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n关闭中...")
        reminder_sys.stop_monitoring()
        server.shutdown()

if __name__ == '__main__':
    run_server()
