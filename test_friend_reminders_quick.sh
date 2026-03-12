#!/bin/bash
# 好友提醒功能快速测试脚本

SERVER="http://47.109.148.176/ai"

echo "========================================="
echo "好友提醒功能快速测试"
echo "========================================="

# 测试用户凭据
USER_A_USERNAME="test_a"
USER_A_PASSWORD="test123"
USER_B_USERNAME="test_b"
USER_B_PASSWORD="test123"

# 1. 用户A登录
echo -e "\n1. 用户A登录..."
RESPONSE_A=$(curl -s -X POST "$SERVER/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USER_A_USERNAME\",\"password\":\"$USER_A_PASSWORD\"}")

TOKEN_A=$(echo $RESPONSE_A | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)
USER_A_ID=$(echo $RESPONSE_A | python3 -c "import sys, json; print(json.load(sys.stdin).get('user_id', ''))" 2>/dev/null)

if [ -z "$TOKEN_A" ]; then
    echo "❌ 用户A登录失败"
    echo "响应: $RESPONSE_A"
    exit 1
fi
echo "✅ 用户A登录成功 (ID: $USER_A_ID)"

# 2. 用户B登录
echo -e "\n2. 用户B登录..."
RESPONSE_B=$(curl -s -X POST "$SERVER/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USER_B_USERNAME\",\"password\":\"$USER_B_PASSWORD\"}")

TOKEN_B=$(echo $RESPONSE_B | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)
USER_B_ID=$(echo $RESPONSE_B | python3 -c "import sys, json; print(json.load(sys.stdin).get('user_id', ''))" 2>/dev/null)

if [ -z "$TOKEN_B" ]; then
    echo "❌ 用户B登录失败"
    echo "响应: $RESPONSE_B"
    exit 1
fi
echo "✅ 用户B登录成功 (ID: $USER_B_ID)"

# 3. 检查好友关系
echo -e "\n3. 检查用户A的好友列表..."
FRIENDS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN_A" "$SERVER/api/social/friends/list")
echo "$FRIENDS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$FRIENDS_RESPONSE"

# 4. 创建好友提醒（用户A给用户B设置提醒，5分钟后）
echo -e "\n4. 用户A给用户B创建提醒..."
REMIND_TIME=$(date -u -v+5M +"%Y-%m-%d %H:%M:%S" 2>/dev/null || date -u -d "+5 minutes" +"%Y-%m-%d %H:%M:%S")
CREATE_RESPONSE=$(curl -s -X POST "$SERVER/api/social/reminders/create" \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d "{
    \"friend_id\": $USER_B_ID,
    \"content\": \"测试好友提醒：记得查看这条消息！\",
    \"remind_time\": \"$REMIND_TIME\",
    \"repeat_type\": \"once\"
  }")

echo "$CREATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$CREATE_RESPONSE"

REMINDER_ID=$(echo $CREATE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('reminder_id', ''))" 2>/dev/null)

if [ -z "$REMINDER_ID" ] || [ "$REMINDER_ID" == "None" ]; then
    echo "❌ 创建提醒失败"
else
    echo "✅ 提醒创建成功 (ID: $REMINDER_ID, 时间: $REMIND_TIME)"
fi

# 5. 用户B查看未确认的好友提醒
echo -e "\n5. 用户B查看未确认的好友提醒..."
UNCONFIRMED_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN_B" "$SERVER/api/social/reminders/unconfirmed")
echo "$UNCONFIRMED_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UNCONFIRMED_RESPONSE"

# 6. 如果有提醒ID，测试确认功能
if [ ! -z "$REMINDER_ID" ] && [ "$REMINDER_ID" != "None" ]; then
    echo -e "\n6. 用户B确认提醒..."
    CONFIRM_RESPONSE=$(curl -s -X POST "$SERVER/api/social/reminders/confirm" \
      -H "Authorization: Bearer $TOKEN_B" \
      -H "Content-Type: application/json" \
      -d "{\"reminder_id\": $REMINDER_ID}")

    echo "$CONFIRM_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$CONFIRM_RESPONSE"

    # 7. 再次查看未确认的提醒（应该为空或不包含刚才的提醒）
    echo -e "\n7. 再次查看未确认的提醒（确认后）..."
    UNCONFIRMED_RESPONSE2=$(curl -s -H "Authorization: Bearer $TOKEN_B" "$SERVER/api/social/reminders/unconfirmed")
    echo "$UNCONFIRMED_RESPONSE2" | python3 -m json.tool 2>/dev/null || echo "$UNCONFIRMED_RESPONSE2"
fi

echo -e "\n========================================="
echo "测试完成！"
echo "========================================="
