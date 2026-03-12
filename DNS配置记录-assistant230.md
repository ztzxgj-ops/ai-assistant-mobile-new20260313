# assistant230.top 域名DNS配置记录

## 需要在阿里云DNS控制台添加以下记录：

### 1. 所有权验证（TXT记录）
```
记录类型：TXT
主机记录：aliyundm
记录值：24379466bfc2eadf22b6c
TTL：600
```

### 2. SPF验证（TXT记录）
```
记录类型：TXT
主机记录：@（或留空，表示主域名）
记录值：v=spf1 include:spf1.dm.aliyun.com -all
TTL：600
```

### 3. DKIM验证（TXT记录）
```
记录类型：TXT
主机记录：aliyun-cn-hangzhou._domainkey
记录值：v=DKIM1; k=rsa; p=MIGfMA0GCSqGSI...（从截图复制完整值）
TTL：600
```

### 4. DMARC验证（TXT记录）
```
记录类型：TXT
主机记录：_dmarc
记录值：v=DMARC1;p=none;rua=mailto:dmar...（从截图复制完整值）
TTL：600
```

### 5. MX验证（MX记录）
```
记录类型：MX
主机记录：@（或留空，表示主域名）
记录值：mx01.dm.aliyun.com
优先级：10
TTL：600
```

---

## 操作步骤：

1. 访问：https://dns.console.aliyun.com
2. 找到域名：assistant230.top
3. 点击"解析设置"
4. 逐条添加上述5条记录
5. 等待10-30分钟让DNS生效
6. 返回邮件推送控制台点击"刷新"按钮验证

---

## 注意事项：

- 主机记录为"@"或留空表示主域名（assistant230.top）
- DKIM和DMARC的记录值很长，需要从截图完整复制
- 如果已经有SPF记录，需要在现有记录中添加 include:spf1.dm.aliyun.com
- MX记录的优先级设置为10
