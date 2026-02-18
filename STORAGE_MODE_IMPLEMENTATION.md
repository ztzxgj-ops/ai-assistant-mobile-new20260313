# 数据存储模式选择功能实现方案

## 功能概述

允许用户在首次登录时选择数据存储模式：
- **云端模式 (cloud)**：数据存储在云服务器MySQL数据库（现有方案）
- **本地模式 (local)**：数据存储在设备本地SQLite数据库（新增方案）

## 实现状态

### ✅ 已完成

1. **数据库改造**
   - 创建迁移脚本：`migrate_add_storage_mode.sql`
   - 添加字段：`storage_mode` (ENUM: 'cloud'/'local')
   - 添加字段：`storage_mode_selected` (TINYINT: 0/1)

2. **后端API**
   - 修改 `user_manager.py`：
     - `get_user_by_username()` - 返回storage_mode字段
     - `get_user_by_id()` - 返回storage_mode字段
     - `login()` - 返回storage_mode和storage_mode_selected
     - `set_storage_mode()` - 设置存储模式
     - `get_storage_mode()` - 获取存储模式

   - 修改 `assistant_web.py`：
     - POST `/api/auth/set-storage-mode` - 设置存储模式
     - POST `/api/auth/get-storage-mode` - 获取存储模式

### 🔄 待实现

3. **Flutter移动端改造**
   - 添加首次登录选择界面
   - 集成sqflite本地数据库
   - 实现数据访问层切换逻辑
   - 本地模式数据管理

4. **电脑端改造**
   - 添加本地SQLite支持
   - 修改数据访问层

5. **数据同步功能**
   - 云端中转同步API
   - 增量同步逻辑
   - 冲突解决策略

6. **数据导出/导入**
   - JSON格式导出
   - SQLite文件导出
   - 数据导入功能

## 数据库迁移

### 执行迁移

```bash
# 连接到云服务器
ssh root@47.109.148.176

# 执行迁移脚本
mysql -u ai_assistant -p ai_assistant < migrate_add_storage_mode.sql

# 验证迁移结果
mysql -u ai_assistant -p -e "USE ai_assistant; DESC users;"
```

### 迁移内容

```sql
-- 添加存储模式字段
ALTER TABLE users
ADD COLUMN storage_mode ENUM('cloud', 'local') DEFAULT 'cloud',
ADD COLUMN storage_mode_selected TINYINT(1) NOT NULL DEFAULT 0;

-- 现有用户默认为云端模式且已选择
UPDATE users
SET storage_mode = 'cloud', storage_mode_selected = 1
WHERE storage_mode_selected = 0;
```

## API接口说明

### 1. 登录接口（已修改）

**请求：** POST `/api/auth/login`

```json
{
  "username": "test",
  "password": "123456"
}
```

**响应：**

```json
{
  "success": true,
  "message": "登录成功",
  "token": "xxx",
  "user_id": 1,
  "username": "test",
  "storage_mode": "cloud",
  "storage_mode_selected": false  // false表示未选择，需要弹出选择界面
}
```

### 2. 设置存储模式（新增）

**请求：** POST `/api/auth/set-storage-mode`

**Headers：** `Authorization: Bearer <token>`

```json
{
  "storage_mode": "local"  // 或 "cloud"
}
```

**响应：**

```json
{
  "success": true,
  "message": "存储模式设置成功",
  "storage_mode": "local"
}
```

### 3. 获取存储模式（新增）

**请求：** POST `/api/auth/get-storage-mode`

**Headers：** `Authorization: Bearer <token>`

**响应：**

```json
{
  "success": true,
  "storage_mode": "local",
  "storage_mode_selected": true
}
```

## Flutter端实现流程

### 1. 登录流程改造

```dart
// 登录成功后检查storage_mode_selected
Future<void> login(String username, String password) async {
  final response = await http.post(
    Uri.parse('$serverUrl/api/auth/login'),
    body: jsonEncode({'username': username, 'password': password}),
  );

  final data = jsonDecode(response.body);

  if (data['success']) {
    // 保存token
    await storage.write(key: 'token', value: data['token']);

    // 检查是否已选择存储模式
    if (!data['storage_mode_selected']) {
      // 显示存储模式选择对话框（强制选择）
      await showStorageModeDialog();
    } else {
      // 根据storage_mode初始化数据访问层
      await initDataLayer(data['storage_mode']);
      // 进入主界面
      Navigator.pushReplacement(context, MaterialPageRoute(
        builder: (context) => HomePage(),
      ));
    }
  }
}
```

### 2. 存储模式选择界面

```dart
Future<void> showStorageModeDialog() async {
  return showDialog(
    context: context,
    barrierDismissible: false,  // 不允许点击外部关闭
    builder: (context) => AlertDialog(
      title: Text('选择数据存储方式'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: Icon(Icons.cloud),
            title: Text('云端存储'),
            subtitle: Text('数据保存在服务器，多设备同步'),
            onTap: () => selectStorageMode('cloud'),
          ),
          ListTile(
            leading: Icon(Icons.phone_android),
            title: Text('本地存储'),
            subtitle: Text('数据保存在本地，隐私性更强'),
            onTap: () => selectStorageMode('local'),
          ),
        ],
      ),
    ),
  );
}

Future<void> selectStorageMode(String mode) async {
  final token = await storage.read(key: 'token');

  final response = await http.post(
    Uri.parse('$serverUrl/api/auth/set-storage-mode'),
    headers: {'Authorization': 'Bearer $token'},
    body: jsonEncode({'storage_mode': mode}),
  );

  final data = jsonDecode(response.body);

  if (data['success']) {
    // 初始化数据访问层
    await initDataLayer(mode);
    // 关闭对话框，进入主界面
    Navigator.pop(context);
    Navigator.pushReplacement(context, MaterialPageRoute(
      builder: (context) => HomePage(),
    ));
  }
}
```

### 3. 数据访问层抽象

```dart
// 定义数据访问接口
abstract class DataRepository {
  Future<List<Message>> getMessages();
  Future<void> saveMessage(Message message);
  Future<List<WorkPlan>> getPlans();
  Future<void> savePlan(WorkPlan plan);
  // ... 其他数据操作方法
}

// 云端实现
class CloudDataRepository implements DataRepository {
  final String serverUrl;
  final String token;

  @override
  Future<List<Message>> getMessages() async {
    final response = await http.get(
      Uri.parse('$serverUrl/api/chats'),
      headers: {'Authorization': 'Bearer $token'},
    );
    // 解析并返回数据
  }

  // ... 其他方法通过HTTP API实现
}

// 本地实现
class LocalDataRepository implements DataRepository {
  final Database db;

  @override
  Future<List<Message>> getMessages() async {
    final List<Map<String, dynamic>> maps = await db.query('messages');
    return List.generate(maps.length, (i) => Message.fromMap(maps[i]));
  }

  // ... 其他方法通过SQLite实现
}

// 初始化数据访问层
Future<void> initDataLayer(String storageMode) async {
  if (storageMode == 'cloud') {
    dataRepository = CloudDataRepository(
      serverUrl: cloudServerUrl,
      token: await storage.read(key: 'token'),
    );
  } else {
    final db = await openLocalDatabase();
    dataRepository = LocalDataRepository(db: db);
  }
}
```

### 4. 本地数据库初始化

```dart
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

Future<Database> openLocalDatabase() async {
  final dbPath = await getDatabasesPath();
  final path = join(dbPath, 'ai_assistant_local.db');

  return await openDatabase(
    path,
    version: 1,
    onCreate: (db, version) async {
      // 创建messages表
      await db.execute('''
        CREATE TABLE messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          role TEXT NOT NULL,
          content TEXT NOT NULL,
          timestamp TEXT NOT NULL
        )
      ''');

      // 创建work_plans表
      await db.execute('''
        CREATE TABLE work_plans (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          content TEXT NOT NULL,
          priority TEXT DEFAULT 'medium',
          status TEXT DEFAULT 'pending',
          due_date TEXT,
          created_at TEXT NOT NULL
        )
      ''');

      // 创建reminders表
      await db.execute('''
        CREATE TABLE reminders (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          content TEXT NOT NULL,
          remind_time TEXT NOT NULL,
          repeat_type TEXT DEFAULT 'once',
          status TEXT DEFAULT 'pending',
          triggered INTEGER DEFAULT 0,
          created_at TEXT NOT NULL
        )
      ''');

      // 创建images表
      await db.execute('''
        CREATE TABLE images (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          filename TEXT NOT NULL,
          file_path TEXT NOT NULL,
          description TEXT,
          created_at TEXT NOT NULL
        )
      ''');
    },
  );
}
```

## 本地模式注意事项

### 1. AI对话功能

本地模式下，AI对话仍需要调用云端API（通义千问），因为：
- AI模型运行在云端
- 需要API密钥认证

**实现方式：**
- 聊天记录存本地
- AI请求发送到云端
- 响应保存到本地数据库

### 2. 用户认证

本地模式下，用户认证仍在云端：
- 登录验证通过云端API
- Token管理在云端
- 用户账号信息在云端

**原因：**
- 统一账号管理
- 支持多设备登录
- 便于数据迁移

### 3. 数据隔离

本地模式下：
- 每个用户的本地数据库独立
- 数据库文件命名：`ai_assistant_local_<user_id>.db`
- 切换账号时切换数据库

## 数据同步方案（可选功能）

### 同步API设计

```
POST /api/sync/upload
- 上传本地数据变更到云端
- 参数：{ data_type, records, last_sync_time }

POST /api/sync/download
- 从云端下载数据变更
- 参数：{ data_type, last_sync_time }
- 返回：{ records, current_time }
```

### 同步策略

1. **增量同步**：只传输变更数据
2. **时间戳比较**：最新时间戳优先
3. **冲突解决**：
   - 同一记录：最新时间戳覆盖
   - 不同记录：合并
4. **同步频率**：
   - 手动触发
   - 应用启动时
   - 定时同步（可配置）

## 数据导出/导入

### 导出功能

```dart
Future<void> exportData() async {
  final data = {
    'version': '1.0',
    'export_time': DateTime.now().toIso8601String(),
    'storage_mode': storageMode,
    'data': {
      'messages': await dataRepository.getMessages(),
      'plans': await dataRepository.getPlans(),
      'reminders': await dataRepository.getReminders(),
    }
  };

  final jsonString = jsonEncode(data);
  final file = File('${documentsPath}/backup_${timestamp}.json');
  await file.writeAsString(jsonString);

  // 分享文件
  Share.shareFiles([file.path], text: '数据备份');
}
```

### 导入功能

```dart
Future<void> importData(String filePath) async {
  final file = File(filePath);
  final jsonString = await file.readAsString();
  final data = jsonDecode(jsonString);

  // 验证版本
  if (data['version'] != '1.0') {
    throw Exception('不支持的备份版本');
  }

  // 导入数据
  for (var message in data['data']['messages']) {
    await dataRepository.saveMessage(Message.fromJson(message));
  }

  for (var plan in data['data']['plans']) {
    await dataRepository.savePlan(WorkPlan.fromJson(plan));
  }

  // ... 导入其他数据
}
```

## 测试计划

### 1. 后端测试

```bash
# 测试登录返回storage_mode
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"123456"}'

# 测试设置存储模式
curl -X POST http://localhost:8000/api/auth/set-storage-mode \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"storage_mode":"local"}'

# 测试获取存储模式
curl -X POST http://localhost:8000/api/auth/get-storage-mode \
  -H "Authorization: Bearer <token>"
```

### 2. Flutter端测试

- [ ] 新用户注册后首次登录，显示选择界面
- [ ] 选择云端模式，数据正常保存到服务器
- [ ] 选择本地模式，数据保存到本地SQLite
- [ ] 本地模式下AI对话功能正常
- [ ] 本地模式下切换账号，数据隔离正确
- [ ] 数据导出功能正常
- [ ] 数据导入功能正常

## 部署步骤

### 1. 部署数据库迁移

```bash
# 上传迁移脚本到服务器
scp migrate_add_storage_mode.sql root@47.109.148.176:/tmp/

# SSH连接服务器
ssh root@47.109.148.176

# 执行迁移
mysql -u ai_assistant -p ai_assistant < /tmp/migrate_add_storage_mode.sql
```

### 2. 部署后端代码

```bash
# 上传修改后的文件
scp user_manager.py root@47.109.148.176:/var/www/ai-assistant/
scp assistant_web.py root@47.109.148.176:/var/www/ai-assistant/

# 重启服务
ssh root@47.109.148.176 "supervisorctl restart ai-assistant"
```

### 3. 部署Flutter应用

```bash
cd ai-assistant-mobile
flutter build ios --release
# 通过Xcode安装到设备
```

## 时间估算

- ✅ 数据库改造：已完成
- ✅ 后端API：已完成
- 🔄 Flutter端改造：3-4天
- 🔄 本地数据库集成：2-3天
- 🔄 数据同步功能：3-5天（可选）
- 🔄 数据导出/导入：1-2天
- 🔄 测试和优化：2-3天

**总计：11-17天**（不含数据同步功能：8-12天）

## 下一步行动

1. **立即执行**：部署数据库迁移和后端代码到云服务器
2. **开始开发**：Flutter端首次登录选择界面
3. **集成SQLite**：添加sqflite依赖，实现本地数据库
4. **测试验证**：完整流程测试

## 相关文件

- `migrate_add_storage_mode.sql` - 数据库迁移脚本
- `user_manager.py` - 用户管理模块（已修改）
- `assistant_web.py` - Web服务器（已修改）
- `STORAGE_MODE_IMPLEMENTATION.md` - 本文档
