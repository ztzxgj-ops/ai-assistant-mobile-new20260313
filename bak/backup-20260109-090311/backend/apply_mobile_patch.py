#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动应用手机端UI优化补丁"""

import re
import sys

def apply_mobile_patch(file_path):
    """应用手机端优化补丁到assistant_web.py"""
    
    print(f"📖 读取文件: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    modified = False
    
    # 1. 在<head>中添加viewport（如果还没有）
    if 'viewport-fit=cover' not in content:
        print("📝 添加viewport meta标签...")
        # 查找<meta charset="UTF-8">
        pattern = r'(<meta charset="UTF-8">)'
        replacement = r'''\1
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#ffffff">'''
        content = re.sub(pattern, replacement, content)
        modified = True
    else:
        print("✓ viewport已存在")
    
    # 2. 在</style>后添加CSS引用（如果还没有）
    if 'mobile_ui_patch.css' not in content:
        print("📝 添加CSS引用...")
        pattern = r'(</style>)'
        replacement = r'''\1
    <link rel="stylesheet" href="/mobile_ui_patch.css">'''
        content = re.sub(pattern, replacement, content, count=1)
        modified = True
    else:
        print("✓ CSS引用已存在")
    
    # 3. 在<body>后添加手机版导航（如果还没有）
    if 'mobile-header' not in content:
        print("📝 添加手机版导航栏...")
        pattern = r'(<body>)'
        replacement = r'''\1
<!-- 手机版顶部导航 -->
<div class="mobile-header">
    <button class="menu-btn" onclick="toggleMobileMenu()"><span>☰</span></button>
    <h1 class="mobile-title">AI助理</h1>
    <button class="new-chat-btn-mobile" onclick="startNewChat()"><span>✏️</span></button>
</div>

<!-- 侧滑菜单 -->
<div class="mobile-menu" id="mobileMenu">
    <div class="menu-overlay" onclick="closeMobileMenu()"></div>
    <div class="menu-drawer">
        <div class="menu-header">
            <div class="menu-user-avatar" id="menuAvatar">👤</div>
            <span class="menu-username" id="menuUsername">用户</span>
        </div>
        <nav class="menu-items">
            <a href="#" onclick="showTab('ai-chat');closeMobileMenu();">💬 AI对话</a>
            <a href="#" onclick="showTab('plans');closeMobileMenu();">📅 工作计划</a>
            <a href="#" onclick="showTab('reminders');closeMobileMenu();">⏰ 提醒</a>
            <a href="#" onclick="showTab('images');closeMobileMenu();">🖼️ 图片</a>
            <a href="#" onclick="showTab('work-records');closeMobileMenu();">📝 工作记录</a>
            <hr>
            <a href="#" onclick="logout();">🚪 退出</a>
        </nav>
    </div>
</div>

<!-- 加载动画 -->
<div class="loading-overlay" id="loadingOverlay">
    <div class="loading-spinner"></div>
</div>
'''
        content = re.sub(pattern, replacement, content, count=1)
        modified = True
    else:
        print("✓ 手机版导航已存在")
    
    # 4. 在</body>前添加JavaScript（如果还没有）
    if 'toggleMobileMenu' not in content:
        print("📝 添加JavaScript函数...")
        pattern = r'(</body>)'
        replacement = r'''
<script>
// 侧滑菜单控制
function toggleMobileMenu(){const m=document.getElementById('mobileMenu');if(m){m.classList.toggle('active');document.body.style.overflow=m.classList.contains('active')?'hidden':'';}}
function closeMobileMenu(){const m=document.getElementById('mobileMenu');if(m){m.classList.remove('active');document.body.style.overflow='';}}
function startNewChat(){const c=document.getElementById('aiChatBox');if(c)c.innerHTML='';const i=document.getElementById('userMessage');if(i){i.value='';i.focus();}}
document.addEventListener('DOMContentLoaded',function(){const u=localStorage.getItem('username');if(u){const mu=document.getElementById('menuUsername');if(mu)mu.textContent=u;const ma=document.getElementById('menuAvatar');if(ma&&u.length>0)ma.textContent=u.charAt(0).toUpperCase();}});
</script>
\1'''
        content = re.sub(pattern, replacement, content)
        modified = True
    else:
        print("✓ JavaScript函数已存在")
    
    # 5. 在do_GET方法中添加CSS路由（如果还没有）
    if "'/mobile_ui_patch.css'" not in content:
        print("📝 添加CSS路由...")
        # 查找do_GET方法中的某个elif
        pattern = r"(elif self\.path == '/api/ai/get_mode':)"
        replacement = r"""elif self.path == '/mobile_ui_patch.css':
            # 提供手机端CSS补丁
            try:
                with open('mobile_ui_patch.css', 'r', encoding='utf-8') as f:
                    css_content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/css; charset=utf-8')
                self.send_header('Cache-Control', 'public, max-age=3600')
                self.end_headers()
                self.wfile.write(css_content.encode('utf-8'))
            except Exception as e:
                self.send_error(404, f'CSS file not found: {e}')
        \1"""
        content = re.sub(pattern, replacement, content, count=1)
        modified = True
    else:
        print("✓ CSS路由已存在")
    
    if modified:
        print(f"\n💾 保存修改到文件...")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 补丁应用成功！")
        return True
    else:
        print("\n✓ 所有补丁已应用，无需修改")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 apply_mobile_patch.py <assistant_web.py路径>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    try:
        apply_mobile_patch(file_path)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
