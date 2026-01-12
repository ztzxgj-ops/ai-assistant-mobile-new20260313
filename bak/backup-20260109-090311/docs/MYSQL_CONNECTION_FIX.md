# MySQL远程连接问题修复指南

## 问题现状

Mac应用已成功打包，但无法连接到云服务器MySQL数据库：
- 错误信息：`(2003, "Can't connect to MySQL server on '47.109.148.176' (timed out)")`
- 原因：云服务器未开放MySQL端口3306的外部访问

## 解决方案

### 第一步：配置阿里云安全组（最常见原因）

1. 登录阿里云控制台：https://ecs.console.aliyun.com

2. 找到你的ECS实例（IP: 47.109.148.176）

3. 点击"安全组" → "配置规则" → "入方向"

4. 添加新规则：
   ```
   协议类型: TCP
   端口范围: 3306/3306
   授权对象: 0.0.0.0/0  (或你的客户端IP以提高安全性)
   描述: MySQL远程访问
   ```

5. 保存规则（立即生效，无需重启）

### 第二步：检查MySQL配置

SSH登录到云服务器后执行：

```bash
# 1. 检查MySQL是否监听3306端口
sudo netstat -tlnp | grep 3306

# 应该看到类似输出：
# tcp  0  0 0.0.0.0:3306  0.0.0.0:*  LISTEN  1234/mysqld

# 如果看到 127.0.0.1:3306（只监听本地），需要修改配置
```

#### 修改MySQL绑定地址（如果需要）

```bash
# 编辑MySQL配置文件
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# 找到这行：
bind-address = 127.0.0.1

# 改为（允许所有IP连接）：
bind-address = 0.0.0.0

# 保存并重启MySQL
sudo systemctl restart mysql
```

### 第三步：验证MySQL用户权限

```bash
# 登录MySQL
mysql -u root -p

# 检查ai_assistant用户的访问权限
SELECT user, host FROM mysql.user WHERE user='ai_assistant';

# 应该看到：
# +---------------+------+
# | user          | host |
# +---------------+------+
# | ai_assistant  | %    |   <-- % 表示允许任何IP
# +---------------+------+

# 如果host显示为'localhost'，需要修改：
DROP USER 'ai_assistant'@'localhost';
CREATE USER 'ai_assistant'@'%' IDENTIFIED BY 'ai_assistant_2024';
GRANT ALL PRIVILEGES ON ai_assistant.* TO 'ai_assistant'@'%';
FLUSH PRIVILEGES;
```

### 第四步：测试连接

在你的Mac上测试端口连通性：

```bash
# 测试端口是否开放
nc -zv -w 5 47.109.148.176 3306

# 成功输出示例：
# Connection to 47.109.148.176 port 3306 [tcp/mysql] succeeded!

# 测试MySQL连接（需要安装mysql客户端）
mysql -h 47.109.148.176 -u ai_assistant -p
# 输入密码：ai_assistant_2024
```

### 第五步：重新测试应用

配置完成后，双击运行 `AI个人助理.app`，应该能正常启动并连接数据库。

## 常见问题

### Q1: 修改安全组后仍然无法连接？

**检查是否有多层防火墙：**
```bash
# 在服务器上检查防火墙状态
sudo ufw status
sudo iptables -L -n | grep 3306

# 如果ufw启用，添加规则：
sudo ufw allow 3306/tcp
```

### Q2: 担心安全性问题？

**方法1：限制IP访问（推荐）**
```sql
-- 只允许特定IP访问
CREATE USER 'ai_assistant'@'你的客户端公网IP' IDENTIFIED BY 'ai_assistant_2024';
GRANT ALL PRIVILEGES ON ai_assistant.* TO 'ai_assistant'@'你的客户端公网IP';
```

**方法2：使用更强的密码**
```sql
ALTER USER 'ai_assistant'@'%' IDENTIFIED BY '复杂密码!@#$%';
```
记得同步修改 `~/Library/Application Support/AIAssistant/mysql_config.json` 中的密码。

**方法3：配置SSL连接**（更高级）

### Q3: 如何查看我的公网IP？

在Mac终端执行：
```bash
curl ifconfig.me
```

将显示的IP添加到安全组的授权对象中，替代 `0.0.0.0/0`

## 验证清单

- [ ] 阿里云安全组已添加3306端口入站规则
- [ ] MySQL bind-address设置为 0.0.0.0
- [ ] MySQL用户host设置为 '%' 或具体IP
- [ ] nc测试端口连通性成功
- [ ] 应用能正常启动并连接数据库

## 后续优化建议

1. **定期更换数据库密码**
2. **配置SSL加密连接**（防止密码明文传输）
3. **启用MySQL慢查询日志**（监控性能）
4. **配置自动备份**（防止数据丢失）
5. **监控异常连接**（检测暴力破解尝试）

---

完成配置后，你的AI助理应用将可以从任何地方（Mac/Windows/Android）连接到云端数据库，实现真正的跨设备使用。
