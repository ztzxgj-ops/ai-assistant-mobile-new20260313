# 部署检查清单

## 部署前检查

- [x] 代码已提交到 git
- [x] macOS 应用已构建成功（75.7MB）
- [x] 没有编译错误
- [x] 文档已更新

## 部署步骤

### 1. 文档部署（已完成）
- [x] 部署 LATEST_BUILD_NOTES.md 到服务器
- [x] 部署 CATEGORY_QUERY_FIX_EXPLANATION.md 到服务器
- [x] 创建 /var/www/ai-assistant/docs/ 目录

### 2. 本地测试（必须）
- [ ] 打开最新的 macOS 应用（构建时间：3月12日 23:55）
- [ ] 切换到本地模式
- [ ] 在"临时"类别中添加测试记录
- [ ] 输入"临时"查询
- [ ] 验证本地记录显示
- [ ] 验证云端记录显示
- [ ] 验证列表格式正确（有 ○ 符号）
- [ ] 验证"+"按钮可用
- [ ] 验证完成任务功能

### 3. 用户通知
- [ ] 准备更新说明
- [ ] 通知用户下载新版本
- [ ] 说明新功能

### 4. 监控
- [ ] 监控用户反馈
- [ ] 检查是否有错误报告
- [ ] 监控应用性能

## 关键改进点

✅ **本地数据可见性**
- 本地模式下添加的记录现在能显示在类别列表中

✅ **数据合并**
- 自动合并本地 SQLite 和云端 MySQL 的数据

✅ **列表格式**
- 符合应用设计规范
- 支持完整的列表交互

✅ **用户体验**
- 无缝的本地+云端数据查询
- 一致的列表显示格式

## 构建信息

- **提交哈希**：0cf9be8（主项目）、7ba48e1（Flutter 子模块）
- **构建时间**：2026-03-12
- **应用大小**：75.7MB
- **构建路径**：`build/macos/Build/Products/Release/忘了吗.app`

## 回滚计划

如果出现问题：
```bash
# 查看提交历史
git log --oneline -5

# 回滚到之前的版本
git revert <commit-hash>

# 重新构建
flutter clean && flutter pub get && flutter build macos --release
```

## 相关文档

- `DEPLOYMENT_NOTES_20260312.md` - 详细部署说明
- `CATEGORY_QUERY_FIX_EXPLANATION.md` - 技术说明
- `CATEGORY_QUERY_FIX_TEST.md` - 测试指南
- `LATEST_BUILD_NOTES.md` - 版本说明

---

**部署状态**：✅ 准备就绪

**下一步**：执行本地测试，然后通知用户
