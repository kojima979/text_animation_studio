#!/usr/bin/env python3
"""
Typewriter animation GIF generator with Japanese support.
Usage: python typewriter_gif.py [config.yaml]
"""

import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

DEFAULTS = {
    "text": "こんにちは、世界！\nHello, World!\nこれはサンプルです。",
    "output": "typewriter.gif",
    "font_path": "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "font_size": 36,
    "color": "#FFFFFF",
    "char_delay": 80,
    "cursor_blink_interval": 500,
    "blink_count": 3,
    "end_delay": 2000,
    "padding": 20,
    "loop": False,
    "cursor": "▌",
}


def load_config(path: str | None) -> dict:
    config = DEFAULTS.copy()
    if path:
        with open(path, encoding="utf-8") as f:
            config.update(yaml.safe_load(f))
    return config


def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def get_font(font_path: str, font_size: int) -> ImageFont.FreeTypeFont:
    if not Path(font_path).exists():
        raise FileNotFoundError(
            f"フォントが見つかりません: {font_path}\n"
            "config.yaml の font_path を確認してください。"
        )
    return ImageFont.truetype(font_path, font_size)


def measure_canvas(lines: list, font, padding: int) -> tuple:
    """テキスト寸法からキャンバスサイズと行高を返す。"""
    probe = "あAg|"
    bbox = font.getbbox(probe)
    row_height = (bbox[3] - bbox[1]) + 6

    max_width = 0
    for line in lines:
        if line:
            b = font.getbbox(line)
            max_width = max(max_width, b[2] - b[0])

    cursor_w = font.getbbox("▌")[2] - font.getbbox("▌")[0]
    width = max_width + cursor_w + 2 * padding
    height = len(lines) * row_height + 2 * padding
    return width, height, row_height


def make_frame(
    lines: list,
    char_pos: int,
    show_cursor: bool,
    font,
    color_rgb: tuple,
    cursor: str,
    canvas_size: tuple,
    row_height: int,
    padding: int,
) -> Image.Image:
    """1フレーム分の RGBA 画像を生成する。"""
    img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    remaining = char_pos
    y = padding

    for line in lines:
        line_len = len(line)

        if remaining > line_len:
            # このラインは全文タイプ済み
            if line:
                draw.text((padding, y), line, font=font, fill=color_rgb + (255,))
            remaining -= line_len
        else:
            # このラインをタイプ中（または末尾）
            typed = line[:remaining]
            if typed:
                draw.text((padding, y), typed, font=font, fill=color_rgb + (255,))

            # カーソル位置
            if typed:
                b = font.getbbox(typed)
                cx = padding + (b[2] - b[0])
            else:
                cx = padding

            if show_cursor:
                draw.text((cx, y), cursor, font=font, fill=color_rgb + (255,))

            break  # 未タイプのラインは描画しない

        y += row_height

    return img


def to_palette_frame(img_rgba: Image.Image, bg_marker=(3, 3, 3)) -> tuple:
    """RGBA フレームを GIF 用パレットモード画像に変換する。"""
    alpha = img_rgba.split()[3]
    text_rgb = img_rgba.convert("RGB")
    bg = Image.new("RGB", img_rgba.size, bg_marker)

    # alpha 閾値で 1-bit 透明に変換
    mask = alpha.point(lambda p: 255 if p >= 128 else 0)
    result = Image.composite(text_rgb, bg, mask)

    img_p = result.quantize(colors=255)

    # パレット中で bg_marker に最も近いインデックスを透明色とする
    palette = img_p.getpalette()
    num_entries = len(palette) // 3
    trans_idx, min_dist = 0, float("inf")
    for i in range(num_entries):
        r, g, b = palette[i * 3 : i * 3 + 3]
        d = (r - bg_marker[0]) ** 2 + (g - bg_marker[1]) ** 2 + (b - bg_marker[2]) ** 2
        if d < min_dist:
            min_dist, trans_idx = d, i

    return img_p, trans_idx


def create_gif(config: dict) -> None:
    text = config["text"].rstrip("\n")
    lines = text.split("\n")
    total_chars = sum(len(l) for l in lines)

    font = get_font(config["font_path"], config["font_size"])
    color_rgb = hex_to_rgb(config["color"])
    cursor = config["cursor"]
    padding = config["padding"]

    w, h, row_height = measure_canvas(lines, font, padding)
    canvas_size = (w, h)

    char_delay = config["char_delay"]
    blink_interval = config["cursor_blink_interval"]
    blink_count = config["blink_count"]
    end_delay = config["end_delay"]

    frames, durations = [], []
    trans_idx = 0

    def add_frame(pos, show_cursor, delay_ms):
        nonlocal trans_idx
        img = make_frame(lines, pos, show_cursor, font, color_rgb, cursor, canvas_size, row_height, padding)
        p, t = to_palette_frame(img)
        frames.append(p)
        durations.append(delay_ms)
        trans_idx = t

    # タイプ中フレーム（0 文字 → 全文字）
    for pos in range(total_chars + 1):
        add_frame(pos, True, char_delay)

    # 終了後カーソル点滅
    for _ in range(blink_count):
        add_frame(total_chars, False, blink_interval)
        add_frame(total_chars, True, blink_interval)

    # 最終フレーム（カーソル非表示で停止）
    add_frame(total_chars, False, end_delay)

    output = config["output"]
    loop_count = 0 if config["loop"] else 1  # 0=無限, 1=1回再生

    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=loop_count,
        transparency=trans_idx,
        disposal=2,
    )
    total_sec = sum(durations) / 1000
    print(f"生成完了: {output}  ({len(frames)} フレーム, {total_sec:.1f}秒)")


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    config = load_config(config_path)
    create_gif(config)


if __name__ == "__main__":
    main()
