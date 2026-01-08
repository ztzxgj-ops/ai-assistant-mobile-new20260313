# 快速修复指南 - 3分钟解决MySQL连接问题

## 问题
Mac应用无法连接到云服务器MySQL：`(2003, "Can't connect to MySQL server on '47.109.148.176' (timed out)")`

## 最可能的原因（90%的情况）
**阿里云安全组未开放3306端口**

## 快速修复步骤

### 方案A：阿里云控制台配置（推荐，最简单）

1. **打开阿里云控制台**
   ```
   https://ecs.console.aliyun.com
   ```

2. **找到你的服务器实例**
   - 查找IP: 47.109.148.176
   - 点击实例ID进入详情页

3. **配置安全组**
   ```
   点击左侧菜单"安全组"
   → 点击"配置规则"
   → 点击"入方向"
   → 点击"添加规则"
   ```

4. **添加MySQL规则**
   ```
   授权策略: 允许
   协议类型: 自定义TCP
   端口范围: 3306/3306
   授权对象: 0.0.0.0/0
   描述: MySQL远程访问
   ```

5. **保存**（立即生效，无需重启）

6. **验证**
   在Mac终端执行：
   ```bash
   nc -zv -w 5 47.109.148.176 3306
   ```

   如果显示 `succeeded!` 则成功，重新打开应用即可。

---

### 方案B：服务器端检查（如果方案A无效）

1. **SSH登录云服务器**
   ```bash
   ssh root@47.109.148.176
   ```

2. **运行诊断脚本**（已为你准备好）

   先在本地上传脚本到服务器：
   ```bash
   scp diagnose_mysql.sh root@47.109.148.176:/root/
   ```

   然后在服务器上执行：
   ```bash
   chmod +x diagnose_mysql.sh
   sudo ./diagnose_mysql.sh
   ```

3. **根据诊断结果修复**

   **如果提示 "MySQL只监听本地"：**
   ```bash
   sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
   # 找到: bind-address = 127.0.0.1
   # 改为: bind-address = 0.0.0.0
   # 保存后重启:
   sudo systemctl restart mysql
   ```

   **如果提示 "用户host为localhost"：**
   ```bash
   mysql -u root -p
   ```
   ```sql
   DROP USER 'ai_assistant'@'localhost';
   CREATE USER 'ai_assistant'@'%' IDENTIFIED BY 'ai_assistant_2024';
   GRANT ALL PRIVILEGES ON ai_assistant.* TO 'ai_assistant'@'%';
   FLUSH PRIVILEGES;
   EXIT;
   ```

---

## 修复后测试

### 1. Mac端口测试
```bash
nc -zv -w 5 47.109.148.176 3306
```
**期望输出：** `Connection to 47.109.148.176 port 3306 [tcp/mysql] succeeded!`

### 2. 运行应用
双击 `AI个人助理.app`

**期望结果：**
- 3秒内自动打开浏览器
- 浏览器显示登录页面
- 能正常注册/登录

---

## 仍然无法连接？

**检查列表：**
- [ ] 阿里云安全组已添加3306规则
- [ ] 服务器MySQL服务正在运行: `systemctl status mysql`
- [ ] MySQL绑定地址为0.0.0.0（不是127.0.0.1）
- [ ] MySQL用户host为'%'（不是'localhost'）
- [ ] 服务器防火墙未阻止3306: `sudo ufw status`

**获取帮助：**
1. 运行服务器端的 `diagnose_mysql.sh` 脚本
2. 将输出结果发给开发者
3. 检查 `MYSQL_CONNECTION_FIX.md` 详细文档

---

## 安全提示

当前配置允许任何IP连接MySQL（`0.0.0.0/0`），**适合测试和个人使用**。

**如需提高安全性：**

1. **限制IP访问**（推荐）
   - 查看你的公网IP: `curl ifconfig.me`
   - 安全组授权对象改为你的IP: `你的IP/32`

2. **使用强密码**
   ```sql
   ALTER USER 'ai_assistant'@'%' IDENTIFIED BY '复杂密码!@#$123';
   ```
   记得同步修改 `~/Library/Application Support/AIAssistant/mysql_config.json`

3. **配置SSL连接**（高级）

---

**预计修复时间：** 3-5分钟（主要是配置安全组）
**难度：** ⭐⭐☆☆☆（简单）
