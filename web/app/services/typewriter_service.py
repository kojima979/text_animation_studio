"""Typewriter GIF アニメーション生成サービス。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageFont

from app.core.fonts import get_default_font, get_font_by_id
from app.core.storage import job_manager
from app.models.schemas import TypewriterRequest

_TYPEWRITER_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent / "typewriter"
if str(_TYPEWRITER_DIR) not in sys.path:
    sys.path.insert(0, str(_TYPEWRITER_DIR))

import typewriter_gif as tw_core  # noqa: E402


def _rgba_to_gif_palette(rgba_img: Image.Image) -> Image.Image:
    """RGBA画像をGIF用パレット画像（透明インデックス=0）に変換する。"""
    alpha = np.array(rgba_img.split()[3])
    rgb = rgba_img.convert("RGB")
    quantized = rgb.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=0)
    palette = quantized.getpalette() or [0] * (255 * 3)

    new_palette = [0, 0, 0] + palette[: 255 * 3]
    p_arr = np.array(quantized, dtype=np.uint8) + 1
    p_arr[alpha < 128] = 0

    result = Image.fromarray(p_arr, mode="P")
    result.putpalette(new_palette)
    return result


def generate_typewriter_gif(req: TypewriterRequest, job_id: str) -> None:
    """Typewriter GIF を生成し、JobManager を更新する。"""
    try:
        job_manager.update_job(job_id, status="running", progress=5.0, message_key="status.preparing")

        font_info = get_font_by_id(req.font_id) or get_default_font()
        font: ImageFont.FreeTypeFont = ImageFont.truetype(str(font_info.file_path), req.font_size)

        text = req.text.rstrip("\n")
        lines: List[str] = text.split("\n")
        total_chars = sum(len(line) for line in lines)

        color_rgb: Tuple[int, int, int] = tw_core.hex_to_rgb(req.color)
        is_transparent = req.background_color.lower() == "transparent"
        bg_rgb: Tuple[int, int, int] = (0, 0, 0) if is_transparent else tw_core.hex_to_rgb(req.background_color)

        w, h, row_height = tw_core.measure_canvas(lines, font, req.padding)
        canvas_size = (w, h)

        # 全フレーム数 = (0..total_chars) + (blink_count * 2) + 最終フレーム
        total_frames = (total_chars + 1) + (req.blink_count * 2) + 1
        frames: List[Image.Image] = []
        durations: List[int] = []

        def add_frame(pos: int, show_cursor: bool, delay_ms: int) -> None:
            rgba_img: Image.Image = tw_core.make_frame(
                lines,
                pos,
                show_cursor,
                font,
                color_rgb,
                req.cursor,
                canvas_size,
                row_height,
                req.padding,
            )
            if is_transparent:
                frame_p = _rgba_to_gif_palette(rgba_img)
            else:
                bg_img = Image.new("RGB", canvas_size, bg_rgb)
                bg_img.paste(rgba_img, (0, 0), rgba_img)
                frame_p = bg_img.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=0)

            frames.append(frame_p)
            durations.append(delay_ms)

            current_idx = len(frames)
            pct = 10.0 + (current_idx / max(1, total_frames)) * 80.0
            job_manager.update_job(job_id, progress=pct, message_key="status.rendering")

        for pos in range(total_chars + 1):
            add_frame(pos, True, req.char_delay)

        for _ in range(req.blink_count):
            add_frame(total_chars, False, req.cursor_blink_interval)
            add_frame(total_chars, True, req.cursor_blink_interval)

        add_frame(total_chars, False, req.end_delay)

        job_manager.update_job(job_id, progress=92.0, message_key="status.encoding")

        out_path = job_manager.allocate_output_path("typewriter", "gif")
        loop_count = 0 if req.loop else 1

        save_kwargs: dict = {
            "save_all": True,
            "append_images": frames[1:],
            "duration": durations,
            "loop": loop_count,
            "disposal": 2,
        }
        if is_transparent:
            save_kwargs["transparency"] = 0

        frames[0].save(str(out_path), **save_kwargs)

        job_manager.update_job(
            job_id,
            status="completed",
            progress=100.0,
            message_key="status.completed",
            output_filename=out_path.name,
            output_format="gif",
            file_size_bytes=out_path.stat().st_size,
        )
    except Exception as exc:
        job_manager.update_job(
            job_id,
            status="failed",
            progress=0.0,
            message_key="status.failed",
            error_detail=str(exc),
        )
