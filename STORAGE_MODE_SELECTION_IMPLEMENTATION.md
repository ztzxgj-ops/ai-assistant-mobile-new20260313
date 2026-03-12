# 存储模式选择功能实现说明

## 功能描述

用户第一次注册成功登录时，系统会强制弹出窗口提醒用户选择储存位置（云端或本地），选择后才能继续使用应用。

## 实现内容

### 1. 数据库修改

**文件**: `add_storage_mode_fields.sql`

在`users`表中添加两个字段：
- `storage_mode`: VARCHAR(20)，默认值'cloud'，存储模式（cloud/local）
- `storage_mode_selected`: TINYINT(1)，默认值0，是否已选择存储模式

**执行状态**: ✅ 已在云服务器数据库执行成功

### 2. Flutter应用修改

**文件**: `ai-assistant-mobile/lib/pages/register_page.dart`

修改内容：
1. 导入`StorageModeDialog`组件
2. 在注册成功后检查`user.storageModeSelected`字段
3. 如果为`false`，显示存储模式选择对话框（强制选择，不可关闭）
4. 如果为`true`，直接跳转到主页

**关键代码**:
```dart
// 检查是否需要选择存储模式
if (user.storageModeSelected == false) {
  // 显示存储模式选择对话框（强制选择）
  await _showStorageModeDialog(user);
} else {
  // 已选择存储模式，直接跳转到主页
  Navigator.of(context).pushAndRemoveUntil(
    MaterialPageRoute(
      builder: (_) => MainPage(user: user),
    ),
    (route) => false,
  );
}
```

**编译状态**: ✅ iOS Release版本编译成功 (46.5MB)

### 3. 后端API支持

**文件**: `user_manager.py`

`login()`方法已经返回`storage_mode`和`storage_mode_selected`字段：
```python
return {
    'success': True,
    'message': '登录成功',
    'token': token,
    'user_id': user['id'],
    'username': user['username'],
    'storage_mode': user.get('storage_mode', 'cloud'),
    'storage_mode_selected': bool(user.get('storage_mode_selected', 0))
}
```

**状态**: ✅ 无需修改，已支持

## 测试步骤

### 测试场景1：新用户注册

1. 打开移动应用
2. 点击"注册"
3. 填写用户名、邮箱、验证码、密码
4. 点击"注册"
5. **预期结果**: 注册成功后，自动弹出存储模式选择对话框
6. 选择"云端存储"或"本地存储"
7. **预期结果**: 选择后跳转到主页面，可以正常使用

### 测试场景2：已有用户首次登录

1. 使用已存在的用户账号登录（storage_mode_selected=0）
2. **预期结果**: 登录成功后，自动弹出存储模式选择对话框
3. 选择存储模式
4. **预期结果**: 选择后跳转到主页面

### 测试场景3：已选择存储模式的用户

1. 使用已选择过存储模式的用户登录（storage_mode_selected=1）
2. **预期结果**: 登录成功后，直接跳转到主页面，不弹出对话框

### 测试场景4：对话框不可关闭

1. 在存储模式选择对话框显示时
2. 尝试点击对话框外部区域
3. **预期结果**: 对话框不会关闭，必须选择一个选项

## 部署步骤

### 1. 数据库迁移

```bash
# 已完成
ssh root@47.109.148.176
mysql -u ai_assistant -p'ai_assistant_2024' ai_assistant < /tmp/add_storage_mode_fields.sql
```

### 2. 安装Flutter应用

```bash
# 方式1：通过Xcode安装（推荐）
1. 打开Xcode
2. 打开 ai-assistant-mobile/ios/Runner.xcworkspace
3. 连接iOS设备
4. 选择设备作为目标
5. 点击运行按钮安装应用

# 方式2：命令行安装（可能超时）
cd ai-assistant-mobile
flutter install
```

### 3. 验证部署

运行测试步骤，确认功能正常工作。

## 技术细节

### 存储模式对话框

**文件**: `ai-assistant-mobile/lib/widgets/storage_mode_dialog.dart`

对话框特性：
- `barrierDismissible: false` - 不允许点击外部关闭
- 提供两个选项：云端存储、本地存储
- 选择后回调`onModeSelected(mode)`
- 自动更新用户的`storageMode`和`storageModeSelected`字段

### 数据流程

```
用户注册
  ↓
后端创建用户（storage_mode_selected=0）
  ↓
自动登录，返回用户信息
  ↓
Flutter检查storageModeSelected
  ↓
false → 显示选择对话框
  ↓
用户选择存储模式
  ↓
更新User对象（storageModeSelected=true）
  ↓
跳转到主页面
```

## 注意事项

1. **已有用户**: 数据库中已存在的用户，`storage_mode_selected`默认为0，首次登录时会弹出选择对话框
2. **不可跳过**: 对话框设置为强制选择，用户必须选择一个选项才能继续
3. **一次性选择**: 选择后`storage_mode_selected`设置为1，之后不再弹出
4. **可修改**: 用户可以在设置页面修改存储模式，但不会再次弹出首次选择对话框

## 相关文件

- `add_storage_mode_fields.sql` - 数据库迁移脚本
- `ai-assistant-mobile/lib/pages/register_page.dart` - 注册页面修改
- `ai-assistant-mobile/lib/widgets/storage_mode_dialog.dart` - 存储模式选择对话框
- `user_manager.py` - 后端用户管理（已支持相关字段）
- `deploy_storage_mode_fix.sh` - 部署脚本

## 完成状态

- ✅ 数据库迁移完成
- ✅ Flutter代码修改完成
- ✅ iOS应用编译成功
- ⏳ 等待安装测试
