#!/bin/bash
# 批量修复umbrella header文件中的import语句

echo "开始修复umbrella header文件..."

# 修复SDWebImage
FILE="./ai-assistant-mobile/ios/Pods/Target Support Files/SDWebImage/SDWebImage-umbrella.h"
if [ -f "$FILE" ]; then
    echo "修复 SDWebImage-umbrella.h..."
    sed -i '' 's/#import "\(.*\)\.h"/#import <SDWebImage\/\1.h>/g' "$FILE"
fi

# 修复其他可能有问题的文件
for umbrella in ./ai-assistant-mobile/ios/Pods/Target\ Support\ Files/*/\*-umbrella.h; do
    if [ -f "$umbrella" ]; then
        # 提取模块名（去掉-umbrella.h后缀）
        module=$(basename "$umbrella" | sed 's/-umbrella.h//')

        # 检查文件是否包含双引号import
        if grep -q '^#import "' "$umbrella"; then
            echo "修复 $module..."
            # 替换双引号import为尖括号import
            sed -i '' "s/#import \"\(.*\)\.h\"/#import <$module\/\1.h>/g" "$umbrella"
        fi
    fi
done

echo "修复完成！"
