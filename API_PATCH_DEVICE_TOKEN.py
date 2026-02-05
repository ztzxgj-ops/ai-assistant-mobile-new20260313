"""
assistant_web.py 添加设备Token管理API的补丁说明

需要在assistant_web.py中添加以下内容：

1. 在文件顶部导入部分添加：
   from mysql_manager import DeviceTokenManager
   from fcm_push_service import get_fcm_service

2. 在 __init__ 方法中初始化：
   self.device_token_manager = DeviceTokenManager(self.db)
   self.fcm_service = get_fcm_service()

3. 在 do_POST 方法中添加以下路由（在其他API路由之后）：

"""

# ============ 添加到 do_POST 方法中 ============

# 保存设备token
elif self.path == '/api/device/register-token':
    user_id = self.require_auth()
    if user_id is None:
        return

    try:
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        device_token = data.get('device_token')
        device_type = data.get('device_type')  # 'ios' or 'android'
        device_name = data.get('device_name')
        device_model = data.get('device_model')
        app_version = data.get('app_version')

        if not device_token or not device_type:
            self.send_json_response({
                'status': 'error',
                'message': '缺少必要参数'
            }, 400)
            return

        # 保存设备token
        success = self.device_token_manager.save_device_token(
            user_id=user_id,
            device_token=device_token,
            device_type=device_type,
            device_name=device_name,
            device_model=device_model,
            app_version=app_version
        )

        if success:
            self.send_json_response({
                'status': 'success',
                'message': '设备token已注册'
            })
        else:
            self.send_json_response({
                'status': 'error',
                'message': '注册失败'
            }, 500)

    except Exception as e:
        print(f"❌ 注册设备token失败: {e}")
        self.send_json_response({
            'status': 'error',
            'message': str(e)
        }, 500)

# 停用设备token
elif self.path == '/api/device/deactivate-token':
    user_id = self.require_auth()
    if user_id is None:
        return

    try:
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        device_token = data.get('device_token')

        if not device_token:
            self.send_json_response({
                'status': 'error',
                'message': '缺少device_token参数'
            }, 400)
            return

        # 停用设备token
        success = self.device_token_manager.deactivate_device_token(device_token)

        if success:
            self.send_json_response({
                'status': 'success',
                'message': '设备token已停用'
            })
        else:
            self.send_json_response({
                'status': 'error',
                'message': '停用失败'
            }, 500)

    except Exception as e:
        print(f"❌ 停用设备token失败: {e}")
        self.send_json_response({
            'status': 'error',
            'message': str(e)
        }, 500)

# 测试推送通知
elif self.path == '/api/device/test-push':
    user_id = self.require_auth()
    if user_id is None:
        return

    try:
        # 获取用户的所有活跃设备token
        devices = self.device_token_manager.get_user_device_tokens(user_id, active_only=True)

        if not devices:
            self.send_json_response({
                'status': 'error',
                'message': '没有找到活跃的设备token'
            }, 404)
            return

        # 提取device_token列表
        device_tokens = [d['device_token'] for d in devices]

        # 发送测试通知
        result = self.fcm_service.send_reminder_notification(
            device_tokens=device_tokens,
            reminder_content='这是一条测试推送通知',
            reminder_id=None
        )

        self.send_json_response({
            'status': 'success' if result.get('success') or result.get('success_count', 0) > 0 else 'error',
            'message': '推送通知已发送',
            'result': result
        })

    except Exception as e:
        print(f"❌ 测试推送失败: {e}")
        self.send_json_response({
            'status': 'error',
            'message': str(e)
        }, 500)


# ============ 添加到 do_GET 方法中 ============

# 获取用户的设备列表
elif self.path == '/api/device/list':
    user_id = self.require_auth()
    if user_id is None:
        return

    try:
        devices = self.device_token_manager.get_user_device_tokens(user_id, active_only=False)

        # 转换datetime为字符串
        for device in devices:
            for key in ['created_at', 'updated_at', 'last_used_at']:
                if key in device and device[key]:
                    device[key] = device[key].isoformat() if hasattr(device[key], 'isoformat') else str(device[key])

        self.send_json_response({
            'status': 'success',
            'devices': devices
        })

    except Exception as e:
        print(f"❌ 获取设备列表失败: {e}")
        self.send_json_response({
            'status': 'error',
            'message': str(e)
        }, 500)
