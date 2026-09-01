#!/usr/bin/env python3
"""
图片验证码生成器
"""

import random
import string
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import os

class CaptchaGenerator:
    def __init__(self):
        self.width = 160  # 宽度保持
        self.height = 38  # 匹配输入框高度
        self.font_size = 32  # 适应38px高度的字体大小
        self.cached_font = None  # 缓存字体对象，避免重复加载
        
    def generate_text(self, length=4):
        """生成随机验证码文本"""
        # 使用数字和大写字母，排除容易混淆的字符
        chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
        return ''.join(random.choice(chars) for _ in range(length))
    
    def create_image(self, text):
        """创建验证码图片"""
        # 创建图片，使用浅灰色背景
        image = Image.new('RGB', (self.width, self.height), color=(248, 249, 250))
        draw = ImageDraw.Draw(image)
        
        # 添加背景噪点（减少数量，避免过度干扰）
        for _ in range(50):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            draw.point((x, y), fill=self._random_light_color())
        
        # 添加干扰线（减少数量）
        for _ in range(3):
            x1 = random.randint(0, self.width)
            y1 = random.randint(0, self.height)
            x2 = random.randint(0, self.width)
            y2 = random.randint(0, self.height)
            draw.line([(x1, y1), (x2, y2)], fill=self._random_light_color(), width=1)
        
        # 绘制文字
        try:
            # 优先使用缓存的字体对象
            if self.cached_font is not None:
                font = self.cached_font
            else:
                # 尝试使用系统字体 - 优化字体加载逻辑
                font_paths = [
                    '/System/Library/Fonts/Menlo.ttc',      # macOS 首选字体，性能更好
                    '/System/Library/Fonts/SFNSMono.ttf',   # macOS
                    '/System/Library/Fonts/Geneva.ttf',     # macOS
                    '/System/Library/Fonts/Helvetica.ttc',  # macOS
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',  # Linux
                    'C:/Windows/Fonts/arial.ttf',           # Windows
                ]
                
                font = None
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        try:
                            font = ImageFont.truetype(font_path, self.font_size)
                            self.cached_font = font  # 缓存字体对象
                            break
                        except Exception as e:
                            print(f"字体加载失败 {font_path}: {e}")
                            continue
                
                if font is None:
                    # 使用默认字体，避免字体加载失败导致验证码生成失败
                    font = ImageFont.load_default()
                    self.cached_font = font  # 缓存默认字体
        except Exception as e:
            # 如果出现异常，使用默认字体
            print(f"验证码字体加载异常: {e}")
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # 计算文字位置 - 更精确的居中
        try:
            # 使用textbbox获取更准确的文本尺寸
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            # 兼容旧版本PIL
            text_width = draw.textlength(text, font=font)
            text_height = self.font_size
        
        # 居中计算，增大字母占比
        start_x = (self.width - text_width) // 2
        start_y = (self.height - text_height) // 2 - 2  # 稍微上移，增大字母占比
        
        # 绘制每个字符，减少随机偏移以保持字母清晰
        char_spacing = text_width // len(text)
        for i, char in enumerate(text):
            char_x = start_x + i * char_spacing + random.randint(-1, 1)  # 减少水平偏移
            char_y = start_y + random.randint(-2, 2)  # 减少垂直偏移
            
            # 使用更深的颜色确保可读性
            color = self._random_dark_color()
            draw.text((char_x, char_y), char, fill=color, font=font)
        
        return image
    
    def _random_light_color(self):
        """生成随机浅色（用于噪点和干扰线）"""
        return (
            random.randint(180, 220),
            random.randint(180, 220),
            random.randint(180, 220)
        )
    
    def _random_dark_color(self):
        """生成随机深色（用于文字，确保可读性）"""
        colors = [
            (33, 37, 41),      # 深灰色
            (220, 53, 69),     # 红色
            (13, 110, 253),    # 蓝色
            (25, 135, 84),     # 绿色
            (102, 16, 242),    # 紫色
            (255, 193, 7),     # 黄色（深一点）
        ]
        return random.choice(colors)
    
    def generate_captcha(self):
        """生成验证码图片和文本"""
        text = self.generate_text()
        image = self.create_image(text)
        
        # 转换为base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_data = buffer.getvalue()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        return text, f"data:image/png;base64,{image_base64}"

# 全局验证码生成器实例
captcha_generator = CaptchaGenerator()

if __name__ == '__main__':
    # 测试验证码生成
    generator = CaptchaGenerator()
    text, image_data = generator.generate_captcha()
    print(f"验证码文本: {text}")
    print(f"图片数据长度: {len(image_data)}")
    print("验证码生成成功！")