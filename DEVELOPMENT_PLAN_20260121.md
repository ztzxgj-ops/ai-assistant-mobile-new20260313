# 开发计划 - 2026年1月21日

## 任务概述
本次开发包含10个独立任务，涉及移动端UI改进、功能增强和后端数据清理。

## 任务列表

### 组1：私聊界面功能增强（3个任务）
**负责代理：chat-features-agent**

1. **任务1：朋友私聊界面增加好友是否阅读显示**
   - 文件：`ai-assistant-mobile/lib/main.dart`（私聊界面部分）
   - 需求：显示消息已读/未读状态
   - 技术方案：添加消息已读状态字段，UI显示已读标记

2. **任务2：好友发送新消息时，app有新消息提示**
   - 文件：`ai-assistant-mobile/lib/main.dart`
   - 需求：新消息通知
   - 技术方案：使用 Flutter local notifications 或系统通知

3. **任务9：朋友私聊界面输入框增加发送文件功能**
   - 文件：`ai-assistant-mobile/lib/main.dart`
   - 需求：支持发送文件
   - 技术方案：使用 file_picker 插件

### 组2：UI样式修复（2个任务）
**负责代理：ui-style-agent**

4. **任务3：手机夜晚模式下，私聊界面输入框文字颜色修改为深色**
   - 文件：`ai-assistant-mobile/lib/main.dart`
   - 需求：夜间模式文字可见性
   - 技术方案：检测主题模式，动态调整文字颜色

5. **任务4：app对话界面、私聊界面，文本复制、粘贴提示改为中文**
   - 文件：`ai-assistant-mobile/lib/main.dart`
   - 需求：本地化文本操作提示
   - 技术方案：自定义 TextSelectionControls

### 组3：留言墙功能增强（3个任务）
**负责代理：guestbook-agent**

6. **任务5：清空留言墙此前的测试内容**
   - 文件：数据库操作
   - 需求：清理测试数据
   - 技术方案：SQL DELETE 语句

7. **任务7：留言墙图片用户点击后可放大观看和下载**
   - 文件：`ai-assistant-mobile/lib/pages/guestbook_page.dart`
   - 需求：图片查看器
   - 技术方案：使用 photo_view 插件

8. **任务8：手机版留言墙发贴时增加可见范围功能**
   - 文件：`ai-assistant-mobile/lib/pages/post_sticky_note_page.dart`
   - 需求：全世界可见、指定好友可见、仅自己可见
   - 技术方案：添加可见性选择器，后端支持

### 组4：UI优化（2个任务）
**负责代理：ui-optimization-agent**

9. **任务6：app私聊界面输入框旁取消表情按键**
   - 文件：`ai-assistant-mobile/lib/main.dart`
   - 需求：移除表情按钮
   - 技术方案：删除相关UI代码

10. **任务10：app上传文件选项中增加照片选择**
    - 文件：`ai-assistant-mobile/lib/main.dart`
    - 需求：支持照片选择
    - 技术方案：使用 image_picker 插件

## 并行开发策略

### 阶段1：准备工作（串行）
- 创建开发日志文件
- 备份当前代码
- 检查依赖项

### 阶段2：并行开发（4个代理同时工作）
- **Agent 1 (chat-features-agent)**：任务1、2、9
- **Agent 2 (ui-style-agent)**：任务3、4
- **Agent 3 (guestbook-agent)**：任务5、7、8
- **Agent 4 (ui-optimization-agent)**：任务6、10

### 阶段3：集成测试（串行）
- 合并所有代码
- 本地测试
- 修复冲突

### 阶段4：部署（串行）
- 部署到云服务器
- 生产环境测试
- 完成报告

## 技术依赖

### Flutter 插件需求
- `file_picker`: ^5.0.0 （文件选择）
- `image_picker`: ^0.8.0 （图片选择）
- `photo_view`: ^0.14.0 （图片查看）
- `flutter_local_notifications`: ^9.0.0 （本地通知）

### 数据库变更
- `messages` 表：添加 `is_read` 字段
- `guestbook` 表：添加 `visibility` 字段

## 预计时间
- 准备工作：5分钟
- 并行开发：20-30分钟
- 集成测试：10分钟
- 部署：5分钟
- **总计：40-50分钟**

## 风险评估
1. **低风险**：UI样式修改（任务3、4、6）
2. **中风险**：功能增强（任务1、2、7、8、9、10）
3. **低风险**：数据清理（任务5）

## 成功标准
- ✅ 所有10个任务完成
- ✅ 本地测试通过
- ✅ 部署到生产环境
- ✅ 生产环境测试通过
- ✅ 开发日志完整记录
