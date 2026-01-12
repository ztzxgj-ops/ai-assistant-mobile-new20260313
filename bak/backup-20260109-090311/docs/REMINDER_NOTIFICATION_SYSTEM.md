# AI助理提醒通知系统 - 完整说明

## ✅ 已完成的工作

### 问题诊断
之前的提醒系统有一个**致命缺陷**：
- ❌ 提醒通知只在**云服务器**上显示（macOS系统通知）
- ❌ 用户在浏览器/应用中**根本看不到**

### 解决方案

#### 方案架构
```
┌─────────────────────────────────────┐
│   Mac App (Electron)                │
│                                      │
│   1. 每10秒自动检查到期提醒         │
│   2. 使用macOS原生通知 ✅           │
│   3. 声音 + 弹窗                    │
└─────────────────────────────────────┘
            ↓ HTTP API
┌─────────────────────────────────────┐
│   云服务器 (47.109.148.176)        │
│                                      │
│   /api/reminders/check              │
│   - 查询到期且未触发的提醒          │
│   - 标记为已触发                    │
│   - 返回提醒列表                    │
└─────────────────────────────────────┘
```

## 📱 现在的工作流程

### 1. 用户创建提醒
```
用户: "1分钟后提醒我开门"
AI: "我将为您设置1分钟后提醒您开门。"
```

→ 提醒被保存到云端MySQL数据库
→ 状态：`pending`, 触发：`0`

### 2. 自动检查（每10秒）
Electron应用在后台持续运行：
```javascript
setInterval(checkDueReminders, 10000); // 每10秒检查
```

→ 调用 `/api/reminders/check` API
→ 查询：`remind_time <= 当前时间 AND triggered = 0`

### 3. 显示通知
当检测到到期的提醒：

**Electron Mac App（您当前使用的）：**
```
✅ macOS原生通知
✅ 系统提示音 (Glass.aiff)
✅ 点击通知 → 聚焦应用窗口
✅ 即使应用最小化也能收到
```

**浏览器版（降级方案）：**
- 优先：Web Notification API
- 降级：页面内浮动通知框

### 4. 标记已触发
```sql
UPDATE reminders
SET triggered = 1, status = 'completed'
WHERE id = xxx
```

## 🎯 当前状态

### 已部署（云服务器）
✅ 后端API `/api/reminders/check`
✅ Python服务器正在运行 (PID: 1843642)
✅ 端口8000监听中

### 已更新（本地Electron）
✅ main.js - macOS原生通知支持
✅ preload.js - 暴露通知API
✅ 前端JavaScript - 自动检查机制

### 已集成（Web界面）
✅ 10秒轮询检查器
✅ Electron原生通知优先
✅ 多级降级策略

## 📝 测试步骤

### 立即测试
1. **打开Mac App**（您当前正在使用的）
   ```bash
   # 如果没运行，双击打开：
   open "/Users/jry/gj/ai助理/xyMac/ai-assistant-electron/dist/mac-arm64/AI个人助理.app"
   ```

2. **创建一个短期提醒**
   ```
   输入: "10秒后提醒我测试通知"
   或: "1分钟后提醒我有事"
   ```

3. **等待10-20秒**
   - 系统会自动检查
   - 到时间后会显示macOS通知
   - 同时播放提示音

4. **验证通知**
   - ✅ 右上角应该出现系统通知
   - ✅ 听到"叮"的提示音
   - ✅ 点击通知会聚焦应用窗口

## 🔧 技术细节

### 后端API实现
```python
# assistant_web.py 第163-204行
elif self.path == '/api/reminders/check':
    """检查到期的提醒（用于浏览器轮询）"""
    user_id = self.require_auth()

    # 查询到期且未触发的提醒
    cursor.execute("""
        SELECT id, content, remind_time
        FROM reminders
        WHERE user_id = %s
        AND status = 'pending'
        AND triggered = 0
        AND remind_time <= %s
        LIMIT 10
    """, (user_id, now))

    # 标记为已触发
    cursor.execute(
        "UPDATE reminders SET triggered = 1, status = 'completed' WHERE id = %s",
        (row[0],)
    )
```

### Electron通知实现
```javascript
// main.js 第269-316行
ipcMain.on('show-notification', (event, { title, body, silent }) => {
    const notification = new Notification({
        title: title || 'AI个人助理',
        body: body || '',
        silent: silent,
        sound: 'Glass', // macOS系统提示音
        urgency: 'critical'
    });

    notification.show();

    // 点击通知时显示主窗口
    notification.on('click', () => {
        if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
        }
    });
});
```

### 前端轮询实现
```javascript
// assistant_web.py 第6463-6593行
async function checkDueReminders() {
    const response = await fetch('/api/reminders/check', {
        headers: { 'Authorization': `Bearer ${token}` }
    });

    const data = await response.json();
    if (data.success && data.reminders.length > 0) {
        data.reminders.forEach(reminder => {
            showReminderNotification(reminder);
        });
    }
}

function startReminderChecker() {
    checkDueReminders(); // 首次立即检查
    setInterval(checkDueReminders, 10000); // 每10秒检查
}
```

## 🎨 通知优先级策略

```
1. Electron原生通知 (最佳)
   ├─ macOS系统通知中心
   ├─ 系统提示音
   └─ 点击可聚焦应用

2. Web Notification API (降级)
   ├─ 浏览器通知权限
   ├─ 需要用户授权
   └─ 限制较多

3. 页面内通知 (最后降级)
   ├─ 右上角浮动框
   ├─ 5秒自动消失
   └─ 无需权限
```

## 📊 数据库字段说明

```sql
reminders 表:
- id: 提醒ID
- user_id: 用户ID
- content: 提醒内容
- remind_time: 提醒时间 (DATETIME)
- status: 状态 (pending/completed/cancelled)
- triggered: 是否已触发 (0/1)
  - 0 = 未触发（会被检测并通知）
  - 1 = 已触发（不再重复通知）
```

## 🔍 调试信息

### 查看浏览器控制台
```javascript
// 应该看到：
"✅ 提醒检查器已启动（10秒间隔）"
"使用Electron原生通知: 📢 任务提醒 开门！！"
```

### 查看Electron主进程日志
```bash
# 应该看到：
"✅ 通知已显示: 📢 任务提醒 开门！！"
```

### 查看服务器日志
```bash
ssh ai-server "tail -f /tmp/ai-assistant.log"
```

## 🚨 常见问题

### Q: 为什么有时候通知延迟10秒？
A: 因为轮询间隔是10秒。提醒时间到了之后，最多10秒内会检测到并通知。

### Q: 可以缩短检查间隔吗？
A: 可以！修改 `setInterval(checkDueReminders, 10000)` 中的 `10000` 为 `5000`（5秒）或更短。但会增加服务器负载。

### Q: Mac没有显示通知？
A: 检查系统设置：
```
系统设置 → 通知 → AI个人助理
确保：
- ✅ 允许通知
- ✅ 显示在通知中心
- ✅ 播放提示音
```

### Q: 浏览器版本能用吗？
A: 能！会降级到Web Notification，但需要用户授权。

### Q: 应用关闭后还能收到通知吗？
A: **不能**。轮询检查在应用内运行，应用关闭后停止检查。
   - 解决方案：最小化应用到后台，不要完全关闭

## 🎯 未来改进方向

### 可选增强
1. **Service Worker**（浏览器版）
   - 即使标签页关闭也能收到通知
   - 需要HTTPS和PWA支持

2. **WebSocket推送**
   - 服务器主动推送，无延迟
   - 不需要轮询，更省电

3. **系统级常驻**
   - Electron应用开机自启
   - 最小化到托盘继续运行

4. **iOS/Android推送**
   - 使用Flutter版应用
   - APNs (iOS) / FCM (Android)

## 📞 支持

如有问题，请检查：
1. Electron应用是否正在运行
2. 浏览器控制台是否有错误
3. 服务器是否响应 `/api/reminders/check`
4. 数据库中提醒的 `triggered` 字段状态

---

**当前版本**: v1.0.0
**更新日期**: 2025-12-22
**状态**: ✅ 已部署并运行
