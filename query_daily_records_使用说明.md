# daily_records 表查询脚本使用说明

## 脚本功能

`query_daily_records.py` 是一个功能完整的查询工具，可以：
- 查询本地SQLite数据库中的 daily_records 表
- 生成云端MySQL数据库的查询脚本
- 支持日期过滤、关键词搜索、限制条数等功能
- 显示详细的记录信息和统计数据

## 基本用法

```bash
python3 query_daily_records.py -u <用户ID> [选项]
```

## 常用示例

### 1. 查询所有记录（默认最近20条）
```bash
python3 query_daily_records.py -u 6
```

### 2. 查询今天的记录
```bash
python3 query_daily_records.py -u 6 --today
```

### 3. 查询最近3天的记录
```bash
python3 query_daily_records.py -u 6 --days 3
```

### 4. 查询指定日期之后的记录
```bash
python3 query_daily_records.py -u 6 --date 2026-02-24
```

### 5. 搜索包含关键词的记录
```bash
python3 query_daily_records.py -u 6 --keyword "测试"
python3 query_daily_records.py -u 6 -k "云端"
```

### 6. 查询最近50条记录
```bash
python3 query_daily_records.py -u 6 --limit 50
python3 query_daily_records.py -u 6 -l 100
```

### 7. 只查询本地数据库
```bash
python3 query_daily_records.py -u 6 --local-only
```

### 8. 只生成云端查询脚本（不查询本地）
```bash
python3 query_daily_records.py -u 6 --cloud-only
```

### 9. 组合使用
```bash
# 查询最近7天包含"本地"关键词的记录，显示最多30条
python3 query_daily_records.py -u 6 --days 7 -k "本地" -l 30

# 查询今天的记录，只看本地数据库
python3 query_daily_records.py -u 6 --today --local-only
```

## 参数说明

| 参数 | 简写 | 说明 | 示例 |
|------|------|------|------|
| `--user-id` | `-u` | **必需** 用户ID | `-u 6` |
| `--date` | `-d` | 查询指定日期之后的记录 | `-d 2026-02-24` |
| `--today` | 无 | 查询今天的记录 | `--today` |
| `--days` | 无 | 查询最近N天的记录 | `--days 7` |
| `--keyword` | `-k` | 搜索关键词（标题或内容） | `-k "测试"` |
| `--limit` | `-l` | 限制返回记录数（默认20） | `-l 50` |
| `--local-only` | 无 | 只查询本地数据库 | `--local-only` |
| `--cloud-only` | 无 | 只生成云端查询脚本 | `--cloud-only` |

## 输出说明

### 本地数据库查询结果

脚本会直接显示本地SQLite数据库的查询结果，包括：
- 每条记录的详细信息（ID、标题、内容、状态、日期等）
- 统计信息（总数、未完成、已完成）

### 云端数据库查询脚本

脚本会生成一个可以直接执行的SSH命令，用于查询云端MySQL数据库。
你可以：
1. 复制生成的脚本直接执行
2. 或者将脚本保存为 `.sh` 文件后执行

## 查看帮助

```bash
python3 query_daily_records.py --help
```

## 数据库位置

### 本地SQLite
```
~/Library/Containers/com.wanglewang.assistant/Data/Documents/local_databases/ai_assistant_local_{用户ID}.db
```

### 云端MySQL
```
服务器: 47.109.148.176
数据库: ai_assistant
表名: daily_records
```

## 注意事项

1. 用户ID必须正确，否则查询不到数据
2. 本地数据库文件必须存在才能查询
3. 云端查询需要SSH访问权限
4. 关键词搜索会同时匹配标题和内容字段
5. 日期过滤使用 `created_at` 字段

## 故障排查

### 本地数据库不存在
```
❌ 数据库文件不存在
```
**解决方法**：检查用户ID是否正确，或者该用户从未使用过本地存储模式

### 没有找到记录
```
⚠️ 没有找到符合条件的记录
```
**解决方法**：
- 检查日期过滤条件是否正确
- 检查关键词是否存在
- 尝试增加 `--limit` 参数值

### 云端查询失败
**解决方法**：
- 检查SSH连接是否正常
- 确认服务器IP地址正确
- 确认有访问权限
