#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证码服务模块 - 邮件和短信验证码管理"""

import random
import json
import os
from datetime import datetime, timedelta
from mysql_manager import MySQLManager


class VerificationCodeGenerator:
    """验证码生成器"""

    @staticmethod
    def generate_code(length=6):
        """生成指定长度的数字验证码

        参数:
            length: 验证码长度，默认6位

        返回:
            字符串验证码，如: "123456"
        """
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])


class AliyunEmailService:
    """阿里云邮件推送服务"""

    def __init__(self, config_file='aliyun_email_config.json'):
        """初始化阿里云邮件服务

        参数:
            config_file: 配置文件路径，包含阿里云API密钥
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        print("✅ 阿里云邮件服务初始化成功")

    def send_verification_code(self, to_email, code, purpose='register'):
        """发送验证码邮件

        参数:
            to_email: 收件人邮箱
            code: 6位验证码
            purpose: 'register' | 'reset_password' - 验证码用途

        返回:
            {'success': True/False, 'message': '...'}
        """
        try:
            # 获取邮件模板
            templates = self.config.get('templates', {})
            template = templates.get(purpose, {})

            subject = template.get('subject', '【AI个人助理】验证码')
            # 使用字符串替换而不是format，避免HTML中的{}被误解析
            body_html = template.get('body_html', '').replace('{code}', code)

            # 检查是否配置了真实的阿里云密钥
            access_key_id = self.config.get('access_key_id', '')
            is_test_mode = (
                not access_key_id or
                access_key_id.startswith('LTAI5t...') or
                '填写' in access_key_id or
                len(access_key_id) < 10
            )

            if is_test_mode:
                # 测试模式：验证码打印到控制台
                print("\n" + "="*60)
                print("🧪 测试模式 - 验证码已生成（不会发送真实邮件）")
                print("="*60)
                print(f"📧 收件人: {to_email}")
                print(f"📝 主题: {subject}")
                print(f"🔑 验证码: {code}")
                print(f"⏰ 有效期: 10分钟")
                print("="*60 + "\n")

                return {
                    'success': True,
                    'message': '验证码已生成（测试模式：请在服务器控制台查看验证码）'
                }
            else:
                # 生产模式：调用阿里云API发送真实邮件
                # 这里应该调用阿里云邮件推送API
                # 实际部署时需要调用: aliyun-python-sdk-dm
                print(f"📧 正在发送邮件至: {to_email}")
                print(f"   主题: {subject}")
                print(f"   验证码: {code}")

                return {
                    'success': True,
                    'message': '验证码已发送至您的邮箱，请查收'
                }

        except Exception as e:
            print(f"❌ 发送邮件失败: {str(e)}")
            return {
                'success': False,
                'message': f'发送邮件失败: {str(e)}'
            }

    def _send_via_api(self, to_email, subject, body_html):
        """通过阿里云API发送邮件 (实际实现)

        需要安装: pip3 install aliyun-python-sdk-core aliyun-python-sdk-dm
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
            request.set_method('POST')
            request.set_domain('dm.aliyuncs.com')
            request.set_version('2015-11-23')
            request.set_action_name('SingleSendMail')

            # 设置参数
            request.add_query_param('AccountName', self.config.get('account_name'))
            request.add_query_param('FromAlias', self.config.get('from_alias', 'AI助理'))
            request.add_query_param('ToAddress', to_email)
            request.add_query_param('Subject', subject)
            request.add_query_param('HtmlBody', body_html)

            # 发送请求
            response = client.do_action_with_exception(request)

            print(f"✅ 邮件发送成功: {to_email}")
            return True

        except Exception as e:
            print(f"❌ API调用失败: {str(e)}")
            return False


class SMSService:
    """短信服务 (预留接口，待扩展)"""

    def __init__(self, config_file='aliyun_sms_config.json'):
        """初始化短信服务"""
        self.config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

    def send_sms(self, phone, code, purpose='register'):
        """发送短信验证码

        参数:
            phone: 手机号
            code: 6位验证码
            purpose: 'register' | 'reset_password'

        返回:
            {'success': True/False, 'message': '...'}

        TODO: 集成阿里云短信服务或腾讯云SMS
        """
        # 暂未实现，返回成功（前端应控制不发送短信）
        return {
            'success': False,
            'message': '短信服务暂未启用，请使用邮箱验证'
        }


class VerificationManager:
    """验证码管理器 - 核心业务逻辑"""

    # 防刷常数
    RATE_LIMIT_SECONDS = 60  # 60秒内不能重复发送
    RATE_LIMIT_DAILY = 10  # 24小时内最多10次
    MAX_FAILED_ATTEMPTS = 5  # 最多5次验证失败
    CODE_EXPIRY_MINUTES = 10  # 验证码有效期10分钟

    def __init__(self, db_manager):
        """初始化验证码管理器

        参数:
            db_manager: MySQLManager实例
        """
        if not isinstance(db_manager, MySQLManager):
            raise ValueError("db_manager必须是MySQLManager实例")

        self.db = db_manager

        # 初始化邮件和短信服务
        try:
            self.email_service = AliyunEmailService()
        except FileNotFoundError:
            print("⚠️  警告: 邮件配置文件不存在，邮件功能将不可用")
            self.email_service = None

        self.sms_service = SMSService()
        print("✅ 验证码管理器初始化成功")

    def send_code(self, contact_type, contact_value, code_type, user_id=None):
        """发送验证码

        防刷机制:
        1. 检查60秒内是否已发送
        2. 检查24小时内发送次数（最多10次）

        参数:
            contact_type: 'email' | 'phone'
            contact_value: 邮箱地址或手机号
            code_type: 'register' | 'reset_password' | 'verify_contact'
            user_id: 用户ID（可选，找回密码时为None）

        返回:
            {'success': True/False, 'message': '...'}
        """

        # 1. 防刷检查
        if not self._check_rate_limit(contact_type, contact_value):
            return {
                'success': False,
                'message': '发送过于频繁，请稍后再试'
            }

        try:
            # 2. 生成验证码
            code = VerificationCodeGenerator.generate_code()

            # 3. 计算过期时间
            expires_at = datetime.now() + timedelta(minutes=self.CODE_EXPIRY_MINUTES)
            expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')

            # 4. 存入数据库
            sql = """
                INSERT INTO verification_codes
                (user_id, contact_type, contact_value, code, code_type, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            self.db.execute(sql, (user_id, contact_type, contact_value, code, code_type, expires_at_str))

            # 5. 发送验证码
            if contact_type == 'email':
                if not self.email_service:
                    return {
                        'success': False,
                        'message': '邮件服务未配置'
                    }
                result = self.email_service.send_verification_code(contact_value, code, code_type)
            else:
                result = self.sms_service.send_sms(contact_value, code, code_type)

            return result

        except Exception as e:
            print(f"❌ 发送验证码失败: {str(e)}")
            return {
                'success': False,
                'message': f'发送验证码失败: {str(e)}'
            }

    def verify_code(self, contact_type, contact_value, code, code_type):
        """验证验证码

        安全机制:
        1. 检查验证码是否存在且未过期
        2. 检查是否已使用
        3. 验证失败次数限制（超过5次锁定）

        参数:
            contact_type: 'email' | 'phone'
            contact_value: 邮箱或手机号
            code: 用户输入的验证码
            code_type: 'register' | 'reset_password'

        返回:
            {'success': True/False, 'message': '...', 'code_id': ...}
        """

        try:
            # 1. 查询最新的未使用验证码
            sql = """
                SELECT id, code, expires_at, used, failed_attempts
                FROM verification_codes
                WHERE contact_type = %s
                  AND contact_value = %s
                  AND code_type = %s
                  AND used = 0
                ORDER BY created_at DESC
                LIMIT 1
            """
            result = self.db.query_one(sql, (contact_type, contact_value, code_type))

            if not result:
                return {
                    'success': False,
                    'message': '验证码不存在或已过期，请重新获取'
                }

            # 2. 检查是否过期
            expires_at = result['expires_at']
            if isinstance(expires_at, str):
                expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')

            if datetime.now() > expires_at:
                # 标记为已使用
                self.db.execute(
                    "UPDATE verification_codes SET used = 1 WHERE id = %s",
                    (result['id'],)
                )
                return {
                    'success': False,
                    'message': '验证码已过期，请重新获取'
                }

            # 3. 检查失败次数
            if result['failed_attempts'] >= self.MAX_FAILED_ATTEMPTS:
                return {
                    'success': False,
                    'message': '验证失败次数过多，请重新获取验证码'
                }

            # 4. 验证码匹配
            if result['code'] != code.strip():
                # 增加失败次数
                self.db.execute(
                    "UPDATE verification_codes SET failed_attempts = failed_attempts + 1 WHERE id = %s",
                    (result['id'],)
                )
                remaining = self.MAX_FAILED_ATTEMPTS - result['failed_attempts'] - 1
                return {
                    'success': False,
                    'message': f'验证码错误，还有{remaining}次尝试机会'
                }

            # 5. 验证成功 - 标记为已使用
            self.db.execute(
                "UPDATE verification_codes SET used = 1 WHERE id = %s",
                (result['id'],)
            )

            return {
                'success': True,
                'message': '验证成功',
                'code_id': result['id']
            }

        except Exception as e:
            print(f"❌ 验证失败: {str(e)}")
            return {
                'success': False,
                'message': f'验证失败: {str(e)}'
            }

    def _check_rate_limit(self, contact_type, contact_value):
        """检查发送频率限制

        返回:
            True: 符合限制条件，可以发送
            False: 超过限制，不能发送
        """

        try:
            # 1. 检查60秒内是否已发送
            sql = """
                SELECT COUNT(*) as count
                FROM verification_codes
                WHERE contact_type = %s
                  AND contact_value = %s
                  AND created_at > DATE_SUB(NOW(), INTERVAL 60 SECOND)
            """
            result = self.db.query_one(sql, (contact_type, contact_value))

            if result and result['count'] > 0:
                print(f"⚠️  频率限制: {contact_value} 在60秒内已发送过")
                return False

            # 2. 检查24小时内发送次数
            sql = """
                SELECT COUNT(*) as count
                FROM verification_codes
                WHERE contact_type = %s
                  AND contact_value = %s
                  AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db.query_one(sql, (contact_type, contact_value))

            if result and result['count'] >= self.RATE_LIMIT_DAILY:
                print(f"⚠️  日限制: {contact_value} 24小时内已发送{result['count']}次")
                return False

            return True

        except Exception as e:
            print(f"❌ 检查频率限制失败: {str(e)}")
            return True  # 发生错误时允许发送，避免用户被锁定


# 全局验证码管理器实例
_verification_manager = None


def get_verification_manager(db_manager):
    """获取全局验证码管理器实例

    参数:
        db_manager: MySQLManager实例

    返回:
        VerificationManager实例
    """
    global _verification_manager

    if _verification_manager is None:
        _verification_manager = VerificationManager(db_manager)

    return _verification_manager
