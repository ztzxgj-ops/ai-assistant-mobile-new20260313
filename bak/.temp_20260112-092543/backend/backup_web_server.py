#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI助理系统备份工具 - Web服务器（增强版）
提供HTTP接口供网页调用备份脚本、历史管理、恢复功能
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import json
import os
import threading
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import sys

# 添加当前目录到路径以导入history manager
sys.path.insert(0, '/Users/gj/编程/ai助理new')
from backup_history_manager import BackupHistoryManager


class BackupHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/':
            # 返回HTML页面
            self.serve_html()
        elif parsed_path.path == '/api/backup':
            # 执行备份
            self.execute_backup()
        elif parsed_path.path == '/api/history':
            # 获取备份历史
            self.get_history()
        elif parsed_path.path == '/api/status':
            # 获取备份状态
            self.get_status()
        else:
            self.send_error(404)

    def do_POST(self):
        """处理POST请求"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/update_notes':
            # 更新备份备注
            self.update_backup_notes()
        elif parsed_path.path == '/api/restore':
            # 恢复备份
            self.restore_backup()
        else:
            self.send_error(404)

    def serve_html(self):
        """返回HTML页面"""
        html_file = '/Users/gj/编程/ai助理new/backup_tool_live.html'

        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()

            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error: {str(e)}")

    def execute_backup(self):
        """执行备份"""
        # 获取备份类型参数
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        backup_type = query_params.get('type', ['standard'])[0]  # 默认为标准备份

        # 根据备份类型选择脚本
        script_map = {
            'standard': '/Users/gj/编程/ai助理new/backup_standard.sh',  # 标准备份：所有内容但不含uploads
            'complete': '/Users/gj/编程/ai助理new/backup_complete_system.sh'  # 完整备份：包含uploads
        }

        script_path = script_map.get(backup_type, script_map['standard'])

        def run_backup():
            try:
                # 执行备份脚本
                process = subprocess.Popen(
                    ['bash', script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding='utf-8',
                    errors='replace'  # 遇到无法解码的字节时替换为�，避免崩溃
                )

                output = []
                backup_dir = None

                for line in process.stdout:
                    output.append(line.strip())
                    # 从输出中提取备份目录名
                    # 新格式: "备份目录: backup-20260109-030127"
                    if '备份目录:' in line:
                        import re
                        match = re.search(r'backup-\d{8}-\d{6}', line)
                        if match:
                            backup_dir = match.group(0)

                process.wait()
                status = 'success' if process.returncode == 0 else 'failed'

                # 记录到历史
                try:
                    manager = BackupHistoryManager()
                    if backup_dir:
                        type_names = {"standard": "标准备份", "complete": "完整备份"}
                        notes = f'备份类型: {type_names.get(backup_type, "标准备份")}'
                        manager.add_backup_record(
                            backup_dir,
                            status=status,
                            notes=notes,
                            error_msg='' if status == 'success' else '\n'.join(output[-5:])
                        )
                except Exception as history_error:
                    output.append(f"历史记录保存失败: {str(history_error)}")

                # 保存结果
                with open('/tmp/backup_result.json', 'w', encoding='utf-8') as f:
                    json.dump({
                        'status': status,
                        'output': output,
                        'returncode': process.returncode,
                        'backup_dir': backup_dir,
                        'backup_type': backup_type
                    }, f, ensure_ascii=False)

            except Exception as e:
                with open('/tmp/backup_result.json', 'w', encoding='utf-8') as f:
                    json.dump({
                        'status': 'error',
                        'output': [str(e)],
                        'returncode': -1,
                        'backup_dir': None,
                        'backup_type': backup_type
                    }, f, ensure_ascii=False)

        # 在后台线程执行备份
        thread = threading.Thread(target=run_backup)
        thread.daemon = True
        thread.start()

        # 立即返回响应
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'started',
            'message': f'备份任务已启动 (类型: {backup_type})',
            'backup_type': backup_type
        }).encode('utf-8'))

    def get_status(self):
        """获取备份状态"""
        try:
            if os.path.exists('/tmp/backup_result.json'):
                with open('/tmp/backup_result.json', 'r', encoding='utf-8') as f:
                    result = json.load(f)

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'running',
                    'message': '备份正在进行中...'
                }).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def get_history(self):
        """获取备份历史"""
        try:
            manager = BackupHistoryManager()
            history = manager.get_history_display()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(history, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            self.send_error(500, str(e))

    def update_backup_notes(self):
        """更新备份备注"""
        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)

            backup_id = data.get('id')
            notes = data.get('notes', '')

            manager = BackupHistoryManager()
            record = manager.update_backup_record(backup_id, notes=notes)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if record:
                self.wfile.write(json.dumps({
                    'status': 'success',
                    'message': '备注已更新',
                    'record': record
                }, ensure_ascii=False).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': '备份记录不存在'
                }, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            self.send_error(500, str(e))

    def restore_backup(self):
        """恢复备份"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(body)
            else:
                data = {}

            backup_dir = data.get('backup_dir')
            bak_path = f'/Users/gj/编程/ai助理new/bak/{backup_dir}'

            if not backup_dir or not os.path.isdir(bak_path):
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': '备份目录不存在'
                }, ensure_ascii=False).encode('utf-8'))
                return

            # 生成恢复脚本
            restore_script = f"""#!/bin/bash
echo "========================================"
echo "  AI助理系统备份恢复工具"
echo "========================================"
echo "开始恢复时间: $(date '+%Y年%m月%d日 %H:%M:%S')"
echo ""

BACKUP_PATH="/Users/gj/编程/ai助理new/bak/{backup_dir}"
SERVER_IP="47.109.148.176"
SERVER_USER="root"
SERVER_PASSWORD="gyq3160GYQ3160"
SERVER_PATH="/var/www/ai-assistant"

# 检查备份文件
CODE_BACKUP=$(ls $BACKUP_PATH/ai-assistant-backup-*.tar.gz 2>/dev/null | head -1)
DB_BACKUP=$(ls $BACKUP_PATH/ai_assistant_db_backup-*.sql 2>/dev/null | head -1)

if [ -z "$CODE_BACKUP" ] || [ -z "$DB_BACKUP" ]; then
    echo "❌ 备份文件不完整"
    exit 1
fi

echo "📦 检测到备份文件:"
echo "   代码备份: $(basename $CODE_BACKUP)"
echo "   数据库备份: $(basename $DB_BACKUP)"
echo ""

# 上传备份到服务器
echo "📤 上传备份文件到服务器..."
sshpass -p "$SERVER_PASSWORD" scp -o StrictHostKeyChecking=no "$CODE_BACKUP" $SERVER_USER@$SERVER_IP:/tmp/restore_code.tar.gz
sshpass -p "$SERVER_PASSWORD" scp -o StrictHostKeyChecking=no "$DB_BACKUP" $SERVER_USER@$SERVER_IP:/tmp/restore_db.sql

# 在服务器上恢复
echo "⚙️  在服务器上执行恢复..."
sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP << 'RESTORE_CMD'
    echo "停止服务..."
    sudo supervisorctl stop ai-assistant

    echo "恢复代码文件..."
    cd $SERVER_PATH
    tar -xzf /tmp/restore_code.tar.gz

    echo "恢复数据库..."
    mysql -u ai_assistant -p'ai_assistant_2024' ai_assistant < /tmp/restore_db.sql

    echo "启动服务..."
    sudo supervisorctl start ai-assistant

    echo "清理临时文件..."
    rm /tmp/restore_code.tar.gz /tmp/restore_db.sql

    echo "✅ 恢复完成"
RESTORE_CMD

echo ""
echo "========================================"
echo "✅ 恢复流程已完成"
echo "========================================"
"""

            # 保存恢复脚本
            restore_script_path = '/tmp/restore_backup.sh'
            with open(restore_script_path, 'w', encoding='utf-8') as f:
                f.write(restore_script)

            os.chmod(restore_script_path, 0o755)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'success',
                'message': '恢复脚本已生成，请在终端执行以下命令：',
                'command': f'bash {restore_script_path}'
            }, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        """自定义日志输出"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    port = 8888
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, BackupHandler)

    print(f"✅ 备份Web服务器已启动")
    print(f"🌐 访问地址: http://127.0.0.1:{port}")
    print(f"📂 备份目录: ~/Documents/GJ/编程/ai助理new/bak")
    print(f"⏹️  按 Ctrl+C 停止服务器\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n⏹️  服务器已停止")


if __name__ == '__main__':
    main()
