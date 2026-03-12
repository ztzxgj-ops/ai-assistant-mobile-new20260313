#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询 daily_records 表的脚本
支持查询本地SQLite和云端MySQL数据库
"""

import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timedelta

def query_local_daily_records(user_id, date_filter=None, limit=20, keyword=None):
    """查询本地SQLite数据库"""
    print("\n" + "=" * 80)
    print("【本地SQLite数据库】")
    print("=" * 80)

    local_db_path = Path.home() / "Library/Containers/com.wanglewang.assistant/Data/Documents/local_databases" / f"ai_assistant_local_{user_id}.db"

    print(f"📂 路径：{local_db_path}")

    if not local_db_path.exists():
        print("❌ 数据库文件不存在")
        return

    print("✅ 数据库文件存在\n")

    try:
        conn = sqlite3.connect(str(local_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 构建查询条件
        conditions = []
        params = []

        if date_filter:
            conditions.append("created_at >= ?")
            params.append(date_filter)

        if keyword:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查询数据
        query = f"""
            SELECT id, subcategory_id, title, content, status, record_date,
                   mood, weather, tags, is_private, created_at, updated_at
            FROM daily_records
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?;
        """
        params.append(limit)

        cursor.execute(query, params)
        records = cursor.fetchall()

        if records:
            print(f"📋 找到 {len(records)} 条记录：\n")

            for i, record in enumerate(records, 1):
                print(f"{'─' * 80}")
                print(f"记录 #{i}")
                print(f"{'─' * 80}")
                print(f"  ID: {record['id']}")
                print(f"  标题: {record['title']}")
                if record['content']:
                    content = record['content'][:100] + "..." if len(record['content']) > 100 else record['content']
                    print(f"  内容: {content}")
                print(f"  状态: {record['status']}")
                print(f"  子类别ID: {record['subcategory_id']}")
                if record['record_date']:
                    print(f"  记录日期: {record['record_date']}")
                if record['mood']:
                    print(f"  心情: {record['mood']}")
                if record['weather']:
                    print(f"  天气: {record['weather']}")
                if record['tags']:
                    print(f"  标签: {record['tags']}")
                print(f"  是否私密: {'是' if record['is_private'] else '否'}")
                print(f"  创建时间: {record['created_at']}")
                if record['updated_at']:
                    print(f"  更新时间: {record['updated_at']}")
                print()

            # 统计信息
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM daily_records
                WHERE {where_clause};
            """, params[:-1])  # 不包括limit参数

            stats = cursor.fetchone()
            print(f"{'═' * 80}")
            print(f"📊 统计信息（符合条件的所有记录）：")
            print(f"   总数: {stats['total']}")
            print(f"   未完成: {stats['pending']}")
            print(f"   已完成: {stats['completed']}")
            print(f"{'═' * 80}")
        else:
            print("⚠️ 没有找到符合条件的记录")

        conn.close()

    except Exception as e:
        print(f"❌ 查询失败：{e}")
        import traceback
        traceback.print_exc()


def print_cloud_query_script(user_id, date_filter=None, limit=20, keyword=None):
    """生成云端查询脚本"""
    print("\n" + "=" * 80)
    print("【云端MySQL数据库查询脚本】")
    print("=" * 80)
    print("\n执行以下命令查询云端数据：\n")

    # 构建WHERE条件
    conditions = []
    if date_filter:
        conditions.append(f"created_at >= '{date_filter}'")
    if keyword:
        conditions.append(f"(title LIKE '%{keyword}%' OR content LIKE '%{keyword}%')")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    script = f"""ssh root@47.109.148.176 << 'EOF'
cd /var/www/ai-assistant

DB_USER=$(grep '"user"' mysql_config.json | cut -d'"' -f4)
DB_PASS=$(grep '"password"' mysql_config.json | cut -d'"' -f4)
DB_NAME=$(grep '"database"' mysql_config.json | cut -d'"' -f4)

echo "📊 查询云端 daily_records 表"
echo "================================"

# 查询数据
mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SELECT id, subcategory_id, title, content, status, record_date,
       mood, weather, tags, is_private, created_at, updated_at
FROM daily_records
WHERE {where_clause}
ORDER BY created_at DESC
LIMIT {limit};
" 2>/dev/null

echo ""
echo "📊 统计信息："
mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SELECT
    COUNT(*) as 总数,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as 未完成,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as 已完成
FROM daily_records
WHERE {where_clause};
" 2>/dev/null

EOF"""

    print(script)
    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='查询 daily_records 表（本地SQLite和云端MySQL）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  # 查询用户ID为6的所有记录（默认最近20条）
  python3 query_daily_records.py -u 6

  # 查询今天的记录
  python3 query_daily_records.py -u 6 --today

  # 查询最近3天的记录
  python3 query_daily_records.py -u 6 --days 3

  # 查询指定日期之后的记录
  python3 query_daily_records.py -u 6 --date 2026-02-24

  # 搜索包含关键词的记录
  python3 query_daily_records.py -u 6 --keyword "测试"

  # 查询最近50条记录
  python3 query_daily_records.py -u 6 --limit 50

  # 只查询本地数据库
  python3 query_daily_records.py -u 6 --local-only

  # 只生成云端查询脚本
  python3 query_daily_records.py -u 6 --cloud-only
        """
    )

    parser.add_argument('-u', '--user-id', type=int, required=True,
                        help='用户ID')
    parser.add_argument('-d', '--date', type=str,
                        help='查询指定日期之后的记录 (格式: YYYY-MM-DD)')
    parser.add_argument('--today', action='store_true',
                        help='查询今天的记录')
    parser.add_argument('--days', type=int,
                        help='查询最近N天的记录')
    parser.add_argument('-k', '--keyword', type=str,
                        help='搜索关键词（标题或内容）')
    parser.add_argument('-l', '--limit', type=int, default=20,
                        help='限制返回记录数（默认20）')
    parser.add_argument('--local-only', action='store_true',
                        help='只查询本地数据库')
    parser.add_argument('--cloud-only', action='store_true',
                        help='只生成云端查询脚本')

    args = parser.parse_args()

    # 处理日期过滤
    date_filter = None
    if args.today:
        date_filter = datetime.now().strftime('%Y-%m-%d')
    elif args.days:
        date_filter = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    elif args.date:
        date_filter = args.date

    print("=" * 80)
    print("🔍 查询 daily_records 表")
    print("=" * 80)
    print(f"用户ID: {args.user_id}")
    if date_filter:
        print(f"日期过滤: {date_filter} 之后")
    if args.keyword:
        print(f"关键词: {args.keyword}")
    print(f"限制条数: {args.limit}")

    # 查询本地数据库
    if not args.cloud_only:
        query_local_daily_records(args.user_id, date_filter, args.limit, args.keyword)

    # 生成云端查询脚本
    if not args.local_only:
        print_cloud_query_script(args.user_id, date_filter, args.limit, args.keyword)


if __name__ == '__main__':
    main()
