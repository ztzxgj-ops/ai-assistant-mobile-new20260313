# 阿里云邮件推送快速参考

## 🔗 重要链接

- **阿里云控制台**: https://www.aliyun.com
- **邮件推送控制台**: https://dm.console.aliyun.com
- **RAM访问控制**: https://ram.console.aliyun.com
- **云解析DNS**: https://dns.console.aliyun.com
- **官方文档**: https://help.aliyun.com/product/29412.html

## 📋 配置步骤速查

### 1. 开通服务
```
阿里云控制台 → 搜索"邮件推送" → 立即开通 → 选择免费版
```

### 2. 配置域名
```
邮件推送控制台 → 发信域名 → 新建域名 → 输入 mail.yourdomain.com
```

### 3. 添加DNS记录
```
云解析DNS → 选择域名 → 添加记录

TXT记录:
  主机记录: mail
  记录值: v=spf1 include:spf.mxhichina.com -all

MX记录:
  主机记录: mail
  记录值: mxn.mxhichina.com
  优先级: 10
```

### 4. 创建发信地址
```
邮件推送控制台 → 发信地址 → 新建发信地址
  发信地址: noreply@mail.yourdomain.com
  发件人名称: AI个人助理
```

### 5. 创建AccessKey
```
RAM访问控制 → 用户 → 创建用户
  登录名称: dm-api-user
  访问方式: ✓ OpenAPI调用访问

创建后 → 添加权限 → AliyunDirectMailFullAccess
```

### 6. 更新配置
```bash
# 使用配置向导
python3 setup_email_wizard.py

# 或手动编辑
vim aliyun_email_config.json
```

### 7. 测试
```bash
# 检查配置
python3 check_email_config.py

# 检查DNS
./check_dns.sh

# 测试发送
python3 test_email_send.py
```

## 🛠️ 实用命令

### 检查DNS记录
```bash
# SPF记录
nslookup -type=txt mail.yourdomain.com

# MX记录
nslookup -type=mx mail.yourdomain.com

# 清除DNS缓存（macOS）
sudo dscacheutil -flushcache
```

### 安装Python依赖
```bash
# 生产模式需要
pip3 install aliyun-python-sdk-core aliyun-python-sdk-dm
```

### 重启服务
```bash
# 本地开发
python3 assistant_web.py

# 生产服务器
sudo supervisorctl restart ai-assistant
```

## 💰 费用

- **免费额度**: 每天200封
- **超出费用**: 0.5元/千封
- **频率限制**: 每秒10封

## ⚠️ 常见问题

### DNS记录不生效
- 等待10分钟到24小时
- 检查记录是否正确
- 清除本地DNS缓存

### 邮件进入垃圾箱
- 确保SPF记录正确
- 避免敏感词汇
- 考虑添加DKIM记录

### 发送失败
- 检查AccessKey是否正确
- 检查RAM用户权限
- 查看控制台错误日志

## 📞 获取帮助

- **工单系统**: https://workorder.console.aliyun.com
- **技术文档**: https://help.aliyun.com/product/29412.html
- **社区论坛**: https://developer.aliyun.com/ask/

## 🔐 安全提示

- ⚠️ AccessKey Secret只显示一次，请妥善保管
- ⚠️ 不要将AccessKey提交到Git仓库
- ⚠️ 定期更换AccessKey
- ⚠️ 使用RAM子账号，不要使用主账号AccessKey

## 📊 监控

### 查看发送统计
```
邮件推送控制台 → 数据统计 → 查看发送量、成功率等
```

### 查看发送日志
```
邮件推送控制台 → 发送日志 → 查看详细发送记录
```

## 🎯 测试清单

- [ ] 配置文件已创建
- [ ] AccessKey已配置
- [ ] 域名已添加
- [ ] DNS记录已配置
- [ ] DNS记录已生效
- [ ] 域名验证通过
- [ ] 发信地址已创建
- [ ] Python依赖已安装
- [ ] 配置检查通过
- [ ] 测试邮件发送成功
- [ ] 服务器已重启
