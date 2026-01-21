#!/bin/bash
# 修改"记录"类别名称为"其他类"

SERVER_IP="47.109.148.176"
SERVER_USER="root"

echo "🔄 开始修改类别名称..."
echo "服务器：$SERVER_IP"
echo ""

# 1. 查看现有类别
echo "📋 查看现有类别..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOSSH'
mysql -u ai_assistant -p'ai_assistant' ai_assistant << 'EOSQL'
SELECT id, name, code, icon, description FROM categories ORDER BY id;
EOSQL
EOSSH

echo ""
echo "🔍 查找'记录'类别..."

# 2. 查找"记录"类别的ID
RECORD_ID=$(ssh ${SERVER_USER}@${SERVER_IP} << 'EOSSH'
mysql -u ai_assistant -p'ai_assistant' ai_assistant -N -e "SELECT id FROM categories WHERE code = 'record' OR name = '记录' LIMIT 1;"
EOSSH
)

if [ -z "$RECORD_ID" ]; then
    echo "❌ 未找到'记录'类别"
    exit 1
fi

echo "✅ 找到'记录'类别，ID: $RECORD_ID"
echo ""

# 3. 查看该类别下的子类别
echo "📋 查看该类别下的子类别..."
ssh ${SERVER_USER}@${SERVER_IP} << EOSSH
mysql -u ai_assistant -p'ai_assistant' ai_assistant << EOSQL
SELECT id, name, code FROM subcategories WHERE category_id = $RECORD_ID;
EOSQL
EOSSH

echo ""

# 4. 查看该类别下的记录数
echo "📊 查看该类别下的记录数..."
ssh ${SERVER_USER}@${SERVER_IP} << EOSSH
mysql -u ai_assistant -p'ai_assistant' ai_assistant << EOSQL
SELECT COUNT(*) as 记录数 FROM daily_records WHERE subcategory_id IN (SELECT id FROM subcategories WHERE category_id = $RECORD_ID);
EOSQL
EOSSH

echo ""

# 5. 修改类别名称
echo "🔄 修改类别名称为'其他类'..."
ssh ${SERVER_USER}@${SERVER_IP} << EOSSH
mysql -u ai_assistant -p'ai_assistant' ai_assistant << EOSQL
UPDATE categories SET name = '其他类' WHERE id = $RECORD_ID;
EOSQL
EOSSH

echo "✅ 修改完成！"
echo ""

# 6. 验证修改
echo "✅ 验证修改结果..."
ssh ${SERVER_USER}@${SERVER_IP} << EOSSH
mysql -u ai_assistant -p'ai_assistant' ai_assistant << EOSQL
SELECT id, name, code, icon, description FROM categories WHERE id = $RECORD_ID;
EOSQL
EOSSH

echo ""
echo "✅ 类别名称修改成功！"
echo "   - 类别名称：记录 → 其他类"
echo "   - 类别代码：record（不变）"
echo "   - 子类别：保持不变"
echo "   - 记录数据：保持不变"
