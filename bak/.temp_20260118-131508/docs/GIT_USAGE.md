# Git版本控制使用指南

## 概述

本项目已配置Git版本控制，提供4个便捷脚本帮助您管理代码版本。

## 快速开始

### 1. 快速提交修改
修改代码后，快速提交：
```bash
cd /var/www/ai-assistant
./git_commit.sh "修复了图片上传Bug"
```

### 2. 安全更新（推荐）
修改重要文件前，先自动备份：
```bash
./git_safe_update.sh "准备修改AI助手配置"
# 然后进行你的修改
# 修改完成后再次运行
./git_safe_update.sh "AI助手配置修改完成"
```

### 3. 查看历史
查看提交历史和备份标签：
```bash
./git_history.sh        # 查看最近10次提交
./git_history.sh 20     # 查看最近20次提交
```

### 4. 恢复版本
恢复到指定版本：
```bash
./git_restore.sh fe29c3e                    # 恢复到指定提交
./git_restore.sh backup_20251214_104500     # 恢复到备份标签
```

## 脚本详解

### git_commit.sh
**功能**：快速提交当前所有修改
**用法**：`./git_commit.sh "提交说明"`
**适用场景**：日常开发，快速保存修改

### git_safe_update.sh
**功能**：修改前自动备份并创建标签
**用法**：`./git_safe_update.sh "修改说明"`
**适用场景**：
- 修改核心文件前（assistant_web.py, ai_chat_assistant.py等）
- 进行重要功能开发前
- 任何可能需要回滚的操作前

**特点**：
- 自动创建带时间戳的备份标签
- 可以精确恢复到任意备份点
- 不会丢失任何修改

### git_history.sh
**功能**：查看提交历史和备份标签
**用法**：`./git_history.sh [数量]`
**显示内容**：
- 提交历史（图形化显示）
- 所有备份标签
- 当前分支状态
- 未提交的更改

### git_restore.sh
**功能**：恢复到指定版本
**用法**：`./git_restore.sh <commit-hash|tag>`
**安全措施**：
- 恢复前自动备份当前状态
- 需要手动确认操作
- 自动重启服务
- 可以随时撤销恢复操作

## 典型工作流程

### 场景1：日常功能开发
```bash
# 1. 查看当前状态
./git_history.sh

# 2. 开始开发...
vim assistant_web.py

# 3. 测试通过后提交
./git_commit.sh "添加了用户头像上传功能"
```

### 场景2：重要功能修改
```bash
# 1. 修改前备份
./git_safe_update.sh "准备重构AI搜索逻辑"

# 2. 进行修改...
vim ai_chat_assistant.py

# 3. 修改完成后再次备份
./git_safe_update.sh "AI搜索逻辑重构完成"

# 4. 测试，如果有问题可以立即恢复
./git_restore.sh backup_20251214_150000  # 恢复到修改前
```

### 场景3：紧急回滚
```bash
# 1. 查看历史，找到要恢复的版本
./git_history.sh

# 2. 恢复到指定版本
./git_restore.sh backup_20251214_120000

# 3. 验证服务状态
ps aux | grep assistant_web
tail -f server.log
```

## Git基础命令

如果需要使用原生Git命令：

### 查看状态
```bash
git status              # 查看当前状态
git log --oneline -10   # 查看提交历史
git tag                 # 查看所有标签
```

### 提交修改
```bash
git add .                           # 添加所有修改
git commit -m "提交说明"            # 提交
```

### 查看差异
```bash
git diff                            # 查看未暂存的修改
git diff --cached                   # 查看已暂存的修改
git diff HEAD~1                     # 与上一次提交对比
```

### 版本恢复
```bash
git checkout <commit> -- <file>     # 恢复单个文件
git reset --hard <commit>           # 硬重置（危险！）
git revert <commit>                 # 创建反向提交
```

## 最佳实践

1. **频繁提交**：每次完成一个小功能就提交
2. **清晰描述**：提交信息要清楚说明做了什么修改
3. **修改前备份**：重要修改前使用 `git_safe_update.sh`
4. **定期查看**：用 `git_history.sh` 了解项目进展
5. **测试后提交**：确保代码可运行后再提交

## 注意事项

### 已自动忽略的文件（.gitignore）
以下文件不会被Git跟踪：
- 敏感配置：`mysql_config.json`, `ai_config.json`
- 日志文件：`*.log`, `server.log`
- 备份文件：`*.backup`, `*.tar.gz`
- 数据库备份：`*.sql`
- 上传文件：`uploads/`目录
- Python缓存：`__pycache__/`, `*.pyc`
- 临时文件：`*.tmp`, `*.swp`

### 配置文件管理
敏感配置文件已被忽略，可以创建示例文件：
```bash
cp mysql_config.json mysql_config.json.example
git add mysql_config.json.example
git commit -m "添加MySQL配置示例文件"
```

## 故障排除

### 提交被拒绝
如果遇到冲突或错误：
```bash
git status                  # 查看具体问题
git reset --soft HEAD~1     # 撤销最后一次提交（保留修改）
```

### 恢复失败
如果恢复脚本执行失败：
```bash
# 查看最近的备份标签
git tag | grep backup | tail -5

# 手动恢复
git checkout <backup-tag> -- .
git add .
git commit -m "手动恢复"
```

### 服务未重启
恢复后如果服务没有自动重启：
```bash
pkill -f 'python3 assistant_web.py'
nohup python3 assistant_web.py > server.log 2>&1 &
```

## 更多帮助

- Git官方文档：https://git-scm.com/doc
- 查看脚本源码了解详细实现
- 有问题可以查看 `server.log` 和Git日志

---

**创建日期**：2025-12-14
**Git初始提交**：fe29c3e
