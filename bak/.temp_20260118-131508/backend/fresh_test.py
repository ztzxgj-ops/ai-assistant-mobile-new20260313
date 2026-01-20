#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/Users/a1-6/Documents/GJ/贷款管理科/贷款政策调整/202511')

from user_manager import UserManager
import json

user_mgr = UserManager()

# 尝试登录
result = user_mgr.login('7303', '7303')
print("登录结果:", json.dumps(result, ensure_ascii=False, indent=2))

if result.get('success'):
    token = result.get('token')
    print(f"\n获得Token: {token}")
    
    # 验证token
    verify_result = user_mgr.verify_token(token)
    print(f"\nToken验证结果: {json.dumps(verify_result, ensure_ascii=False, indent=2)}")
