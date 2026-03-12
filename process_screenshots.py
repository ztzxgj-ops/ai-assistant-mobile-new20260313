#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
App Store截图处理脚本
- 调整尺寸到1290 x 2796
- 添加功能说明文字
"""

from PIL import Image, ImageDraw, ImageFont
import os

# App Store标准尺寸（iPhone 6.7" Display）
TARGET_WIDTH = 1290
TARGET_HEIGHT = 2796

# 截图目录
SCREENSHOTS_DIR = "/Users/gj/编程/ai助理new/screenshots"
OUTPUT_DIR = "/Users/gj/编程/ai助理new/screenshots/appstore"

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 图片说明文字（根据文件名顺序）
CAPTIONS = {
    "微信图片_20260218185839_33_2.png": "AI智能对话 - 随时对话，智能解答",
    "微信图片_20260218191211_35_2.png": "文件管理 - 安全存储，随时查看",
    "微信图片_20260218192719_37_2.png": "智能保存 - 一键保存重要信息",
    "微信图片_20260218192720_38_2.png": "身份验证 - 安全保护您的数据",
    "微信图片_20260218192721_39_2.png": "任务管理 - 高效规划工作计划",
    "微信图片_20260218192722_40_2.png": "智能提醒 - 定时循环，不再遗忘",
    "微信图片_20260218192949_41_2.png": "快速登录 - 安全便捷的账号认证",
    "微信图片_20260218192950_42_2.png": "社交互动 - 与朋友分享和交流",
    "微信图片_20260218193029_44_2.jpg": "个性定制 - 自定义应用分类",
    "微信图片_20260218222632_45_2.png": "主题切换 - 多种主题随心选择",
    "微信图片_20260218223633_46_2.png": "智能助理 - 让生活更高效"
}

def process_screenshot(input_path, output_path, caption):
    """
    处理单张截图
    1. 调整尺寸到目标尺寸
    2. 添加文字说明
    """
    print(f"处理: {os.path.basename(input_path)}")

    # 打开图片
    img = Image.open(input_path)
    original_width, original_height = img.size

    print(f"  原始尺寸: {original_width} x {original_height}")

    # 计算缩放比例（保持宽高比）
    width_ratio = TARGET_WIDTH / original_width
    height_ratio = TARGET_HEIGHT / original_height

    # 使用较小的比例，确保图片不会被拉伸
    scale_ratio = min(width_ratio, height_ratio)

    # 计算新尺寸
    new_width = int(original_width * scale_ratio)
    new_height = int(original_height * scale_ratio)

    # 调整图片大小
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 创建目标尺寸的白色背景
    result = Image.new('RGB', (TARGET_WIDTH, TARGET_HEIGHT), 'white')

    # 将调整后的图片居中粘贴
    x_offset = (TARGET_WIDTH - new_width) // 2
    y_offset = (TARGET_HEIGHT - new_height) // 2
    result.paste(img_resized, (x_offset, y_offset))

    # 添加文字说明（在底部）
    draw = ImageDraw.Draw(result)

    # 尝试使用系统字体
    try:
        # macOS系统中文字体
        font_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 60)
        font_subtitle = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 40)
    except:
        # 如果找不到字体，使用默认字体
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()

    # 分割标题和副标题
    if " - " in caption:
        title, subtitle = caption.split(" - ", 1)
    else:
        title = caption
        subtitle = ""

    # 在底部添加半透明背景
    overlay = Image.new('RGBA', (TARGET_WIDTH, 300), (0, 0, 0, 180))
    result_rgba = result.convert('RGBA')
    result_rgba.paste(overlay, (0, TARGET_HEIGHT - 300), overlay)
    result = result_rgba.convert('RGB')

    # 重新创建draw对象
    draw = ImageDraw.Draw(result)

    # 计算文字位置（居中）
    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (TARGET_WIDTH - title_width) // 2
    title_y = TARGET_HEIGHT - 250

    # 绘制标题
    draw.text((title_x, title_y), title, fill='white', font=font_title)

    # 绘制副标题
    if subtitle:
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (TARGET_WIDTH - subtitle_width) // 2
        subtitle_y = title_y + 80
        draw.text((subtitle_x, subtitle_y), subtitle, fill='#CCCCCC', font=font_subtitle)

    # 保存处理后的图片
    result.save(output_path, 'PNG', quality=95)
    print(f"  ✅ 已保存: {os.path.basename(output_path)}")
    print(f"  最终尺寸: {TARGET_WIDTH} x {TARGET_HEIGHT}")

def main():
    """主函数"""
    print("="*60)
    print("App Store截图处理工具")
    print("="*60)
    print(f"目标尺寸: {TARGET_WIDTH} x {TARGET_HEIGHT}")
    print(f"输入目录: {SCREENSHOTS_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("="*60)

    # 获取所有截图文件
    files = sorted([f for f in os.listdir(SCREENSHOTS_DIR)
                   if f.endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.')])

    print(f"\n找到 {len(files)} 张截图\n")

    # 处理每张截图
    processed_count = 0
    for i, filename in enumerate(files, 1):
        input_path = os.path.join(SCREENSHOTS_DIR, filename)
        output_filename = f"screenshot_{i:02d}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        # 获取说明文字
        caption = CAPTIONS.get(filename, f"忘了吗 - 功能 {i}")

        try:
            process_screenshot(input_path, output_path, caption)
            processed_count += 1
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")

        print()

    print("="*60)
    print(f"✅ 处理完成！成功处理 {processed_count}/{len(files)} 张截图")
    print(f"输出目录: {OUTPUT_DIR}")
    print("="*60)

if __name__ == "__main__":
    main()
