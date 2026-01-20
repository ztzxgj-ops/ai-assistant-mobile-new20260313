#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动识别用户需求并记录到开发日志
可以通过命令行快速添加需求
"""

import sys
import re
from development_log import DevelopmentLogManager


class AutoRequirementLogger:
    """自动需求记录器"""

    # 需求关键词模式
    REQUIREMENT_PATTERNS = [
        r'(希望|想要|需要|麻烦|请|帮我|帮忙)(.*?)(实现|修复|添加|改进|优化|支持|处理|解决)',
        r'(能不能|可以|可不可以)(.*?)(实现|修复|添加|改进|优化)',
        r'(实现|修复|添加|改进|优化|支持|开发)(.*?)功能',
        r'(有个|发现|遇到)(.*?)(问题|bug|错误)',
    ]

    def __init__(self):
        self.dev_log = DevelopmentLogManager()

    def extract_requirement(self, user_message):
        """从用户消息中提取需求

        Args:
            user_message: 用户的消息内容

        Returns:
            (requirement, details) 或 None
        """
        message = user_message.strip()

        # 检查是否匹配需求模式
        for pattern in self.REQUIREMENT_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                # 提取需求描述（取整句话作为需求）
                requirement = message[:100]  # 限制长度
                details = message if len(message) > 100 else ''
                return (requirement, details)

        # 如果消息较长且包含问号，可能是需求
        if len(message) > 20 and '?' in message:
            return (message[:100], message if len(message) > 100 else '')

        return None

    def add_requirement_from_message(self, user_message):
        """从用户消息添加需求

        Args:
            user_message: 用户的消息内容

        Returns:
            log_id 或 None
        """
        result = self.extract_requirement(user_message)
        if not result:
            return None

        requirement, details = result
        log_id = self.dev_log.add_requirement(requirement, details)
        print(f"✅ 自动识别并添加需求 (ID: {log_id})")
        print(f"   需求: {requirement}")
        if details:
            print(f"   详情: {details[:50]}...")
        return log_id

    def complete_latest_requirement(self, completion_message):
        """完成最新的需求

        Args:
            completion_message: 完成情况描述

        Returns:
            是否成功
        """
        # 获取最新的进行中任务
        in_progress = self.dev_log.get_in_progress_logs()
        if not in_progress:
            print("⚠️ 没有进行中的任务")
            return False

        latest = in_progress[-1]
        success = self.dev_log.update_completion(
            latest['id'],
            completion_message,
            status='completed'
        )

        if success:
            print(f"✅ 已标记任务完成 (ID: {latest['id']})")
            print(f"   需求: {latest['requirement']}")
            print(f"   完成: {completion_message}")

        return success


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  添加需求: python3 auto_log_requirement.py add '需求描述'")
        print("  标记完成: python3 auto_log_requirement.py complete '完成情况'")
        print("  自动识别: python3 auto_log_requirement.py auto '用户消息'")
        sys.exit(1)

    command = sys.argv[1]
    logger = AutoRequirementLogger()

    if command == 'add':
        # 手动添加需求
        requirement = sys.argv[2] if len(sys.argv) > 2 else ''
        details = sys.argv[3] if len(sys.argv) > 3 else ''
        if requirement:
            log_id = logger.dev_log.add_requirement(requirement, details)
            print(f"✅ 添加需求成功 (ID: {log_id})")
        else:
            print("❌ 请提供需求描述")

    elif command == 'complete':
        # 标记最新任务完成
        completion = sys.argv[2] if len(sys.argv) > 2 else '已完成'
        logger.complete_latest_requirement(completion)

    elif command == 'auto':
        # 自动识别需求
        message = sys.argv[2] if len(sys.argv) > 2 else ''
        if message:
            result = logger.add_requirement_from_message(message)
            if not result:
                print("ℹ️ 未识别到需求关键词")
        else:
            print("❌ 请提供用户消息")

    elif command == 'list':
        # 列出所有任务
        logs = logger.dev_log.get_all_logs()
        if not logs:
            print("暂无开发日志")
        else:
            print(f"\n共 {len(logs)} 条开发日志:\n")
            for log in logs:
                status_emoji = {
                    'in_progress': '🔧',
                    'completed': '✅',
                    'cancelled': '❌'
                }.get(log['status'], '❓')

                print(f"{status_emoji} [{log['id']}] {log['requirement']}")
                print(f"    开始: {log['start_time']}")
                if log['completion']:
                    print(f"    完成: {log['completion']}")
                if log['backup_time']:
                    print(f"    已备份: {log['backup_time']}")
                print()

    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
