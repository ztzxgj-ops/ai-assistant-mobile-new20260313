#!/bin/bash
# Flutter iOS构建签名问题修复脚本

FRAMEWORK_PATH="$1"

if [ ! -d "$FRAMEWORK_PATH" ]; then
  echo "Framework not found: $FRAMEWORK_PATH"
  exit 1
fi

# 删除所有扩展属性
find "$FRAMEWORK_PATH" -type f -exec xattr -d com.apple.quarantine {} + 2>/dev/null || true
find "$FRAMEWORK_PATH" -type f -exec xattr -d -r com.apple.macl {} + 2>/dev/null || true

# 删除所有目录的扩展属性
find "$FRAMEWORK_PATH" -type d -exec xattr -d com.apple.quarantine {} + 2>/dev/null || true
find "$FRAMEWORK_PATH" -type d -exec xattr -d -r com.apple.macl {} + 2>/dev/null || true

echo "✅ Framework签名问题已修复"
