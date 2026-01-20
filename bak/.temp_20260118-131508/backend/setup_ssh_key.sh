#!/bin/bash
# 上传SSH公钥到服务器
# 密码: gyq3160GYQ3160

echo "正在上传SSH公钥到服务器..."
echo "请在提示时输入密码: gyq3160GYQ3160"
echo ""

# 方法1: 使用ssh-copy-id（如果可用）
if command -v ssh-copy-id &> /dev/null; then
    echo "使用 ssh-copy-id 上传..."
    ssh-copy-id -i ~/.ssh/id_rsa.pub root@47.109.148.176
else
    # 方法2: 手动复制
    echo "手动上传公钥..."
    cat ~/.ssh/id_rsa.pub | ssh root@47.109.148.176 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo '公钥已添加'"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 公钥上传成功！"
    echo ""
    echo "现在测试免密登录..."
    ssh -o BatchMode=yes -o ConnectTimeout=5 root@47.109.148.176 "echo '✓ 免密登录成功！'"

    if [ $? -eq 0 ]; then
        echo ""
        echo "🎉 SSH免密登录配置完成！"
        echo "以后可以直接使用: ssh root@47.109.148.176"
    else
        echo ""
        echo "⚠️  免密登录测试失败，可能需要重试"
    fi
else
    echo ""
    echo "❌ 上传失败，请手动执行:"
    echo "   cat ~/.ssh/id_rsa.pub | ssh root@47.109.148.176 'cat >> ~/.ssh/authorized_keys'"
fi
