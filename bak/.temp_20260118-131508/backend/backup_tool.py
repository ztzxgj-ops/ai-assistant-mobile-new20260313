#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI助理系统自动备份工具 - GUI版本
功能：备份云服务器代码、配置和数据库到本地
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import os
from datetime import datetime
import json

class BackupTool:
    def __init__(self, root):
        self.root = root
        self.root.title("AI助理系统自动备份工具")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        # 配置
        self.config = {
            "server_ip": "47.109.148.176",
            "server_password": "gyq3160GYQ3160",
            "server_user": "root",
            "server_path": "/var/www/ai-assistant",
            "local_bak_dir": "/Users/gj/编程/ai助理new/bak",
            "db_name": "ai_assistant",
            "db_user": "ai_assistant",
            "db_password": "ai_assistant_2024"
        }
        
        # 历史记录文件
        self.history_file = os.path.join(self.config['local_bak_dir'], 'backup_history.json')
        
        # 创建UI
        self.create_ui()
        
        # 加载历史记录
        self.load_history()
    
    def create_ui(self):
        """创建用户界面"""
        # 标题
        title_frame = tk.Frame(self.root, bg='#667eea', height=80)
        title_frame.pack(fill=tk.X)
        
        title_label = tk.Label(
            title_frame,
            text="🚀 AI助理系统自动备份工具",
            font=("Arial", 20, "bold"),
            bg='#667eea',
            fg='white'
        )
        title_label.pack(pady=20)
        
        # 信息面板
        info_frame = tk.LabelFrame(self.root, text="📊 备份信息", padx=20, pady=15)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        info_grid = tk.Frame(info_frame)
        info_grid.pack(fill=tk.X)
        
        # 第一行
        tk.Label(info_grid, text="服务器地址:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        tk.Label(info_grid, text=self.config['server_ip'], font=("Arial", 10, "bold")).grid(row=0, column=1, sticky=tk.W, padx=10)
        
        tk.Label(info_grid, text="备份目录:", font=("Arial", 10)).grid(row=0, column=2, sticky=tk.W, pady=5, padx=(30, 0))
        tk.Label(info_grid, text=os.path.basename(self.config['local_bak_dir']), font=("Arial", 10, "bold")).grid(row=0, column=3, sticky=tk.W, padx=10)
        
        # 第二行
        tk.Label(info_grid, text="上次备份:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.last_backup_label = tk.Label(info_grid, text="从未备份", font=("Arial", 10, "bold"), fg='#666')
        self.last_backup_label.grid(row=1, column=1, sticky=tk.W, padx=10)
        
        tk.Label(info_grid, text="备份数量:", font=("Arial", 10)).grid(row=1, column=2, sticky=tk.W, pady=5, padx=(30, 0))
        self.backup_count_label = tk.Label(info_grid, text="0 个", font=("Arial", 10, "bold"), fg='#666')
        self.backup_count_label.grid(row=1, column=3, sticky=tk.W, padx=10)
        
        # 备份按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        
        self.backup_btn = tk.Button(
            btn_frame,
            text="🎯 开始备份",
            font=("Arial", 14, "bold"),
            bg='#667eea',
            fg='white',
            width=20,
            height=2,
            cursor='hand2',
            command=self.start_backup_thread
        )
        self.backup_btn.pack()
        
        # 进度条
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate', length=760)
        self.progress.pack()
        
        self.progress_label = tk.Label(progress_frame, text="", font=("Arial", 9), fg='#666')
        self.progress_label.pack(pady=5)
        
        # 日志输出
        log_frame = tk.LabelFrame(self.root, text="📝 备份日志", padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            bg='#1e1e1e',
            fg='#00ff00',
            font=("Monaco", 10),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部按钮
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Button(
            bottom_frame,
            text="📂 打开备份目录",
            command=self.open_backup_dir,
            cursor='hand2'
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            bottom_frame,
            text="🗑️ 清空日志",
            command=self.clear_log,
            cursor='hand2'
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            bottom_frame,
            text="📋 查看历史",
            command=self.show_history,
            cursor='hand2'
        ).pack(side=tk.LEFT, padx=5)
        
    def add_log(self, message, level='INFO'):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # 根据级别设置颜色
        colors = {
            'INFO': '#00ff00',
            'WARN': '#ffcc00',
            'ERROR': '#ff4444',
            'SUCCESS': '#00ff88'
        }
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        self.log_text.insert(tk.END, f"{message}\n", level.lower())
        
        # 配置标签颜色
        self.log_text.tag_config('timestamp', foreground='#888')
        self.log_text.tag_config('info', foreground=colors['INFO'])
        self.log_text.tag_config('warn', foreground=colors['WARN'])
        self.log_text.tag_config('error', foreground=colors['ERROR'])
        self.log_text.tag_config('success', foreground=colors['SUCCESS'])
        
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()
    
    def update_progress(self, value, text=''):
        """更新进度"""
        self.progress['value'] = value
        self.progress_label.config(text=text)
        self.root.update()
    
    def start_backup_thread(self):
        """在新线程中启动备份"""
        self.backup_btn.config(state=tk.DISABLED, text="⏳ 备份中...")
        thread = threading.Thread(target=self.start_backup)
        thread.daemon = True
        thread.start()
    
    def start_backup(self):
        """执行备份"""
        try:
            self.add_log("开始备份流程...", 'INFO')
            self.update_progress(0, '初始化...')
            
            # 调用Shell脚本
            script_path = "/Users/gj/编程/ai助理new/backup_server.sh"
            
            if not os.path.exists(script_path):
                self.add_log(f"备份脚本不存在: {script_path}", 'ERROR')
                self.backup_btn.config(state=tk.NORMAL, text="🎯 开始备份")
                return
            
            # 执行脚本并实时显示输出
            process = subprocess.Popen(
                ['bash', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            progress_map = {
                '检查依赖': 10,
                '创建本地': 20,
                '备份代码': 40,
                '服务器备份创建成功': 50,
                '代码备份完成': 60,
                '数据库导出成功': 70,
                '数据库备份完成': 80,
                '备份说明创建完成': 90,
                '清理旧备份': 95,
                '备份完成': 100
            }
            
            for line in process.stdout:
                line = line.strip()
                if line:
                    # 去除ANSI颜色代码
                    line = self.strip_ansi(line)
                    
                    # 判断日志级别
                    if 'ERROR' in line:
                        self.add_log(line, 'ERROR')
                    elif 'WARN' in line:
                        self.add_log(line, 'WARN')
                    elif '✓' in line or '成功' in line:
                        self.add_log(line, 'SUCCESS')
                    else:
                        self.add_log(line, 'INFO')
                    
                    # 更新进度
                    for keyword, progress in progress_map.items():
                        if keyword in line:
                            self.update_progress(progress, line)
                            break
            
            process.wait()
            
            if process.returncode == 0:
                self.add_log("✅ 备份完成！", 'SUCCESS')
                self.update_progress(100, '备份成功！')
                
                # 播放提示音
                os.system('afplay /System/Library/Sounds/Glass.aiff &')
                
                # 保存历史记录
                self.save_history()
                self.load_history()
                
                messagebox.showinfo("备份成功", "备份已完成！\n请查看日志了解详情。")
            else:
                self.add_log("❌ 备份失败", 'ERROR')
                messagebox.showerror("备份失败", "备份过程中出现错误！\n请查看日志了解详情。")
            
        except Exception as e:
            self.add_log(f"备份出错: {str(e)}", 'ERROR')
            messagebox.showerror("错误", f"备份出错: {str(e)}")
        
        finally:
            self.backup_btn.config(state=tk.NORMAL, text="🎯 开始备份")
    
    def strip_ansi(self, text):
        """去除ANSI颜色代码"""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def open_backup_dir(self):
        """打开备份目录"""
        os.system(f'open "{self.config["local_bak_dir"]}"')
    
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def save_history(self):
        """保存历史记录"""
        history = []
        
        # 加载现有历史
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                pass
        
        # 添加新记录
        history.insert(0, {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'success'
        })
        
        # 只保留最近20条
        history = history[:20]
        
        # 保存
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.add_log(f"保存历史记录失败: {str(e)}", 'WARN')
    
    def load_history(self):
        """加载历史记录"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                if history:
                    self.last_backup_label.config(text=history[0]['time'], fg='#333')
                    self.backup_count_label.config(text=f"{len(history)} 个", fg='#333')
            except:
                pass
    
    def show_history(self):
        """显示历史记录"""
        if not os.path.exists(self.history_file):
            messagebox.showinfo("历史记录", "暂无备份历史")
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # 创建新窗口
            history_window = tk.Toplevel(self.root)
            history_window.title("备份历史")
            history_window.geometry("500x400")
            
            # 标题
            tk.Label(
                history_window,
                text="📋 备份历史记录",
                font=("Arial", 14, "bold")
            ).pack(pady=10)
            
            # 列表
            frame = tk.Frame(history_window)
            frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            # 滚动条
            scrollbar = tk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
            listbox.pack(fill=tk.BOTH, expand=True)
            
            scrollbar.config(command=listbox.yview)
            
            # 填充数据
            for item in history:
                status_emoji = "✅" if item['status'] == 'success' else "❌"
                listbox.insert(tk.END, f"{status_emoji} {item['time']}")
            
            # 关闭按钮
            tk.Button(
                history_window,
                text="关闭",
                command=history_window.destroy,
                width=15
            ).pack(pady=10)
        
        except Exception as e:
            messagebox.showerror("错误", f"加载历史记录失败: {str(e)}")

def main():
    root = tk.Tk()
    app = BackupTool(root)
    root.mainloop()

if __name__ == '__main__':
    main()
