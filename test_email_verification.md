# 📧 邮件验证码测试指南

## 🧪 测试模式说明

当前系统已启用**测试模式**，验证码会打印在服务器控制台，不会发送真实邮件。

### 测试模式触发条件

以下任一条件满足时，系统自动进入测试模式：
- `access_key_id` 为空
- `access_key_id` 以 `LTAI5t...` 开头（占位符）
- `access_key_id` 包含"填写"字样
- `access_key_id` 长度小于10个字符

## 📝 本地测试步骤

### 1. 启动本地服务器

```bash
cd /Users/gj/编程/ai助理new
python3 assistant_web.py
```

服务器会在 `http://localhost:8000` 启动。

### 2. 测试注册流程

**方式A：使用移动App测试**
1. 打开移动app
2. 点击"立即注册"
3. 填写用户名和邮箱
4. 点击"发送验证码"
5. 在服务器控制台查看验证码（会有明显的分隔线）
6. 复制验证码到app中
7. 完成注册

**方式B：使用curl命令测试**

```bash
# 1. 发送验证码
curl -X POST http://localhost:8000/api/verification/send-code \
  -H "Content-Type: application/json" \
  -d '{
    "contact_type": "email",
    "contact_value": "test@example.com",
    "code_type": "register"
  }'

# 2. 从控制台复制验证码（例如：123456）

# 3. 注册用户
curl -X POST http://localhost:8000/api/auth/register-with-verification \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "test123456",
    "email": "test@example.com",
    "verification_code": "123456"
  }'
```

### 3. 查看验证码输出

在服务器控制台会看到类似输出：

```
============================================================
🧪 测试模式 - 验证码已生成（不会发送真实邮件）
============================================================
📧 收件人: test@example.com
📝 主题: 【AI个人助理】注册验证码
🔑 验证码: 123456
⏰ 有效期: 10分钟
============================================================
```

## 🚀 部署到服务器测试

### 1. 部署更新后的代码

```bash
# 本地执行
cd /Users/gj/编程/ai助理new

# 上传修改后的文件
scp verification_service.py root@47.109.148.176:/var/www/ai-assistant/
scp aliyun_email_config.json root@47.109.148.176:/var/www/ai-assistant/

# 重启服务
ssh root@47.109.148.176 "cd /var/www/ai-assistant && sudo supervisorctl restart ai-assistant"
```

### 2. 查看服务器日志

```bash
# 实时查看日志
ssh root@47.109.148.176 "tail -f /var/log/ai-assistant.log"

# 或者查看最近的日志
ssh root@47.109.148.176 "tail -50 /var/log/ai-assistant.log"
```

### 3. 使用移动App测试

1. 打开移动app（会自动连接到 http://47.109.148.176/ai/）
2. 点击"立即注册"
3. 填写信息并发送验证码
4. 在服务器日志中查看验证码
5. 输入验证码完成注册

## 🔧 验证码规则

- **长度**: 6位数字
- **有效期**: 10分钟
- **防刷机制**:
  - 60秒内不能重复发送
  - 24小时内最多发送10次
- **失败限制**: 最多5次验证失败

## 📊 测试检查清单

- [ ] 本地服务器能正常启动
- [ ] 发送验证码API返回成功
- [ ] 控制台能看到验证码输出
- [ ] 验证码格式正确（6位数字）
- [ ] 使用验证码能成功注册
- [ ] 过期验证码会被拒绝（10分钟后）
- [ ] 错误验证码会被拒绝
- [ ] 60秒内重复发送会被限制
- [ ] 服务器部署后功能正常

## 🎯 下一步：配置真实邮件服务

当你准备好配置真实的邮件服务时：

1. **购买域名**（可选，约10元/年）
   - 推荐：阿里云、腾讯云、GoDaddy
   - 例如：`yourdomain.com`

2. **开通阿里云邮件推送**
   - 登录阿里云控制台
   - 搜索"邮件推送"并开通
   - 配置发信域名和发信地址

3. **更新配置文件**
   - 填写真实的 `access_key_id` 和 `access_key_secret`
   - 系统会自动切换到生产模式

4. **安装SDK**
   ```bash
   pip3 install aliyun-python-sdk-core aliyun-python-sdk-dm
   ```

## 💡 提示

- 测试模式完全免费，无需任何费用
- 验证码会保存在数据库中，即使重启服务器也不会丢失
- 可以同时测试多个用户注册
- 建议先在本地测试通过，再部署到服务器

## ❓ 常见问题

**Q: 看不到验证码输出？**
- 检查是否在正确的终端窗口查看
- 确认服务器正在运行
- 查看日志文件：`tail -f /var/log/ai-assistant.log`

**Q: 验证码验证失败？**
- 确认验证码没有过期（10分钟内）
- 检查是否输入了正确的6位数字
- 验证码区分大小写（虽然只有数字）

**Q: 想要关闭测试模式？**
- 在 `aliyun_email_config.json` 中填写真实的阿里云密钥
- 系统会自动检测并切换到生产模式
