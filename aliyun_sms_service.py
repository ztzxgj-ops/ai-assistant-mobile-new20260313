#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阿里云短信服务实现 - 替换verification_service.py中的SMSService类"""

import json
import os


class AliyunSMSService:
    """阿里云短信服务"""

    def __init__(self, config_file='aliyun_sms_config.json'):
        """初始化阿里云短信服务

        参数:
            config_file: 配置文件路径，包含阿里云API密钥和短信模板
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        print("✅ 阿里云短信服务初始化成功")

    def send_sms(self, phone, code, purpose='register'):
        """发送短信验证码

        参数:
            phone: 手机号（11位数字）
            code: 6位验证码
            purpose: 'register' | 'reset_password' | 'verify_contact'

        返回:
            {'success': True/False, 'message': '...'}
        """
        try:
            # 验证手机号格式
            if not self._validate_phone(phone):
                return {
                    'success': False,
                    'message': '手机号格式错误'
                }

            # 获取短信模板
            templates = self.config.get('templates', {})
            template = templates.get(purpose, {})
            template_code = template.get('template_code', '')

            if not template_code or '填写' in template_code:
                # 测试模式：打印验证码到控制台
                return self._test_mode(phone, code, purpose)

            # 检查是否配置了真实的AccessKey
            access_key_id = self.config.get('access_key_id', '')
            is_test_mode = (
                not access_key_id or
                '填写' in access_key_id or
                len(access_key_id) < 10
            )

            if is_test_mode:
                # 测试模式
                return self._test_mode(phone, code, purpose)
            else:
                # 生产模式：调用阿里云API发送真实短信
                return self._send_via_api(phone, code, template_code)

        except Exception as e:
            print(f"❌ 发送短信失败: {str(e)}")
            return {
                'success': False,
                'message': f'发送短信失败: {str(e)}'
            }

    def _validate_phone(self, phone):
        """验证手机号格式

        参数:
            phone: 手机号

        返回:
            True/False
        """
        # 去除空格和特殊字符
        phone = phone.replace(' ', '').replace('-', '')

        # 检查是否是11位数字
        if not phone.isdigit() or len(phone) != 11:
            return False

        # 检查是否以1开头
        if not phone.startswith('1'):
            return False

        return True

    def _test_mode(self, phone, code, purpose):
        """测试模式：验证码打印到控制台

        参数:
            phone: 手机号
            code: 验证码
            purpose: 用途

        返回:
            {'success': True, 'message': '...'}
        """
        sign_name = self.config.get('sign_name', 'AI助理')

        print("\n" + "=" * 60)
        print("🧪 测试模式 - 短信验证码已生成（不会发送真实短信）")
        print("=" * 60)
        print(f"📱 手机号: {phone}")
        print(f"📝 签名: 【{sign_name}】")
        print(f"🔑 验证码: {code}")
        print(f"📋 用途: {purpose}")
        print(f"⏰ 有效期: 10分钟")
        print("=" * 60 + "\n")

        return {
            'success': True,
            'message': '验证码已生成（测试模式：请在服务器控制台查看验证码）'
        }

    def _send_via_api(self, phone, code, template_code):
        """通过阿里云API发送短信（实际实现）

        需要安装: pip3 install aliyun-python-sdk-core aliyun-python-sdk-dysmsapi

        参数:
            phone: 手机号
            code: 验证码
            template_code: 短信模板CODE

        返回:
            {'success': True/False, 'message': '...'}
        """
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkcore.request import CommonRequest

            # 初始化阿里云客户端
            client = AcsClient(
                self.config['access_key_id'],
                self.config['access_key_secret'],
                self.config.get('region', 'cn-hangzhou')
            )

            # 创建请求
            request = CommonRequest()
            request.set_accept_format('json')
            request.set_domain('dysmsapi.aliyuncs.com')
            request.set_method('POST')
            request.set_protocol_type('https')
            request.set_version('2017-05-25')
            request.set_action_name('SendSms')

            # 设置参数
            request.add_query_param('PhoneNumbers', phone)
            request.add_query_param('SignName', self.config.get('sign_name', 'AI助理'))
            request.add_query_param('TemplateCode', template_code)
            request.add_query_param('TemplateParam', json.dumps({'code': code}))

            # 发送请求
            response = client.do_action_with_exception(request)
            response_data = json.loads(response)

            # 检查返回结果
            if response_data.get('Code') == 'OK':
                print(f"✅ 短信发送成功: {phone}")
                return {
                    'success': True,
                    'message': '验证码已发送至您的手机，请查收'
                }
            else:
                error_code = response_data.get('Code', 'Unknown')
                error_message = response_data.get('Message', '未知错误')
                print(f"❌ 短信发送失败: {error_code} - {error_message}")
                return {
                    'success': False,
                    'message': f'发送失败: {error_message}'
                }

        except ImportError:
            print("❌ 缺少依赖: pip3 install aliyun-python-sdk-core")
            return {
                'success': False,
                'message': '短信服务未正确配置，请联系管理员'
            }
        except Exception as e:
            print(f"❌ API调用失败: {str(e)}")
            return {
                'success': False,
                'message': f'发送失败: {str(e)}'
            }


# 使用示例
if __name__ == '__main__':
    # 测试短信服务
    sms_service = AliyunSMSService()

    # 发送测试短信
    result = sms_service.send_sms(
        phone='13800138000',
        code='123456',
        purpose='register'
    )

    print(f"\n发送结果: {result}")
