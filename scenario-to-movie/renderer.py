"""テキストブロックのレイアウト座標を計算する（描画はanimator.pyで行う）"""

import os
from dataclasses import dataclass
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

from docx_parser import TextBlock


@dataclass
class LayoutBlock:
    lines: List[str]
    canvas_y: int
    line_height: int
    font: ImageFont.FreeTypeFont
    font_size: int
    alignment: str
    total_height: int


def _parse_color(color_str: str) -> Tuple[int, int, int]:
    color_str = color_str.strip().lstrip('#')
    r = int(color_str[0:2], 16)
    g = int(color_str[2:4], 16)
    b = int(color_str[4:6], 16)
    return (r, g, b)


def _find_system_font() -> str:
    candidates = [
        '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
        '/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc',
        '/System/Library/Fonts/ヒラギノ明朝 ProN.ttc',
        '/Library/Fonts/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ''


def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    path = font_path or _find_system_font()
    if path and os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default(size=size)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    if not text.strip():
        return []
    lines = []
    current = ''
    tmp = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(tmp)
    for char in text:
        test = current + char
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines if lines else [text]


def compute_layout(blocks: List[TextBlock], config: dict) -> Tuple[List[LayoutBlock], int]:
    """全ブロックのレイアウト座標を計算してLayoutBlockリストとキャンバス高さを返す"""
    video_w = config['resolution'][0]
    font_path = config.get('font_path', '')
    margin_x = config['margin_x']
    line_spacing = config['line_spacing']
    empty_line_h = config['empty_line_height']
    para_spacing = config['paragraph_spacing']
    max_text_w = video_w - 2 * margin_x

    size_body = config['font_size_body']
    size_h1 = config['font_size_heading1']
    size_h2 = config['font_size_heading2']

    font_body = _load_font(font_path, size_body)
    font_h1 = _load_font(font_path, size_h1)
    font_h2 = _load_font(font_path, size_h2)

    def get_font_and_size(block: TextBlock):
        if block.heading_level == 1:
            return font_h1, size_h1
        if block.heading_level == 2:
            return font_h2, size_h2
        return font_body, size_body

    layout_blocks = []
    y = 20

    for block in blocks:
        if not block.text.strip():
            y += empty_line_h
            continue
        font, size = get_font_and_size(block)
        lines = _wrap_text(block.text, font, max_text_w)
        line_h = int(size * line_spacing)
        block_h = len(lines) * line_h + para_spacing

        layout_blocks.append(LayoutBlock(
            lines=lines,
            canvas_y=y,
            line_height=line_h,
            font=font,
            font_size=size,
            alignment=block.alignment,
            total_height=block_h,
        ))
        y += block_h

    canvas_h = y + 20
    return layout_blocks, canvas_h
