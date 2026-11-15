"""Scenario to Movie テキスト解析および動画・アニメーション生成サービス。"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import imageio_ffmpeg
from PIL import Image

from app.core.fonts import get_default_font, get_font_by_id
from app.core.storage import job_manager
from app.models.schemas import ScenarioRequest

_SCENARIO_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent / "scenario-to-movie"


def _ensure_scenario_modules() -> Any:
    """python-docx 非依存で scenario-to-movie モジュールを読み込む。"""
    if str(_SCENARIO_DIR) not in sys.path:
        sys.path.insert(0, str(_SCENARIO_DIR))

    if "docx_parser" not in sys.modules:
        stub = types.ModuleType("docx_parser")

        @dataclass
        class TextBlock:
            text: str
            heading_level: int
            alignment: str

        stub.TextBlock = TextBlock  # type: ignore[attr-defined]
        sys.modules["docx_parser"] = stub

    import animator as sc_animator  # noqa: E402
    import encoder as sc_encoder  # noqa: E402
    import renderer as sc_renderer  # noqa: E402

    return sys.modules["docx_parser"].TextBlock, sc_renderer, sc_animator, sc_encoder


def parse_text_to_blocks(text: str, alignment: str) -> List[Any]:
    """Markdown風直接入力テキストを TextBlock リストへ変換する。"""
    TextBlock, _, _, _ = _ensure_scenario_modules()
    blocks: List[Any] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            blocks.append(TextBlock(text="", heading_level=0, alignment=alignment))
        elif stripped.startswith("## "):
            blocks.append(TextBlock(text=stripped[3:].strip(), heading_level=2, alignment=alignment))
        elif stripped.startswith("# "):
            blocks.append(TextBlock(text=stripped[2:].strip(), heading_level=1, alignment=alignment))
        else:
            blocks.append(TextBlock(text=raw_line, heading_level=0, alignment=alignment))
    return blocks


def _build_config(req: ScenarioRequest, font_path: str) -> Dict[str, Any]:
    return {
        "background_color": req.background_color,
        "font_color": req.font_color,
        "font_path": font_path,
        "font_size_body": req.font_size_body,
        "font_size_heading1": req.font_size_heading1,
        "font_size_heading2": req.font_size_heading2,
        "font_size_final": req.font_size_final,
        "line_spacing": req.line_spacing,
        "empty_line_height": req.empty_line_height,
        "paragraph_spacing": req.paragraph_spacing,
        "margin_x": req.margin_x,
        "resolution": [req.width, req.height],
        "fps": req.fps,
        "scroll_speed": req.scroll_speed,
        "leading_seconds": req.leading_seconds,
        "trailing_seconds": req.trailing_seconds,
        "flyin_duration": req.flyin_duration,
        "landing_y_ratio": req.landing_y_ratio,
        "flyin_bounce": req.flyin_bounce,
        "flyin_rotation_max": req.flyin_rotation_max,
        "flyin_alpha_start": req.flyin_alpha_start,
        "flyin_scale_mode": req.flyin_scale_mode,
        "flyin_scale_min": req.flyin_scale_min,
        "flyin_scale_max": req.flyin_scale_max,
        "flyin_scale_shrink_start": req.flyin_scale_shrink_start,
        "flyin_wander_radius": req.flyin_wander_radius,
        "flyin_wander_freq_min": req.flyin_wander_freq_min,
        "flyin_wander_freq_max": req.flyin_wander_freq_max,
        "gif_fps": req.gif_fps,
        "gif_scale": req.gif_scale,
        "gif_max_frames": req.gif_max_frames,
        "gif_loop": req.gif_loop,
    }


def _encode_image_sequence(
    animator: Any,
    output_path: Path,
    fmt: str,
    config: Dict[str, Any],
    sc_encoder: Any,
    job_id: str,
) -> None:
    fps: float = float(config["gif_fps"])
    scale: float = float(config["gif_scale"])
    video_w, video_h = config["resolution"]
    new_w = max(1, int(video_w * scale))
    new_h = max(1, int(video_h * scale))
    fps, total_frames = sc_encoder._clamp_frames(fps, animator.total_duration, config["gif_max_frames"])
    duration_ms = max(10, int(1000 / fps))

    frames: List[Image.Image] = []
    for i in range(total_frames):
        t = i / fps
        arr = animator.make_frame(t)
        img = Image.fromarray(arr)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        if scale != 1.0:
            img = img.resize((new_w, new_h), Image.LANCZOS)

        if fmt == "gif":
            frames.append(sc_encoder._rgba_to_gif_palette(img))
        else:
            frames.append(img)

        pct = 15.0 + ((i + 1) / max(1, total_frames)) * 75.0
        job_manager.update_job(job_id, progress=pct, message_key="status.rendering")

    job_manager.update_job(job_id, progress=92.0, message_key="status.encoding")
    loop = int(config["gif_loop"])

    if fmt == "gif":
        save_kwargs: Dict[str, Any] = {
            "save_all": True,
            "append_images": frames[1:],
            "duration": duration_ms,
            "loop": loop,
            "disposal": 2,
        }
        if animator.is_transparent:
            save_kwargs["transparency"] = 0
        frames[0].save(str(output_path), **save_kwargs)
    else:
        frames[0].save(
            str(output_path),
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=loop,
        )


def _encode_video_stream(
    animator: Any,
    output_path: Path,
    fmt: str,
    config: Dict[str, Any],
    job_id: str,
) -> None:
    fps: int = int(config["fps"])
    video_w, video_h = config["resolution"]
    total_frames = max(1, int(animator.total_duration * fps) + 1)

    if fmt == "webm":
        writer = imageio_ffmpeg.write_frames(
            str(output_path),
            size=(video_w, video_h),
            fps=fps,
            pix_fmt_in="rgba",
            pix_fmt_out="yuva420p" if animator.is_transparent else "yuv420p",
            codec="libvpx-vp9",
            macro_block_size=1,
            output_params=["-b:v", "0", "-crf", "30"],
        )
        expect_rgba = True
    else:
        # H.264 MP4 は偶数解像度が必要
        even_w = video_w - (video_w % 2)
        even_h = video_h - (video_h % 2)
        writer = imageio_ffmpeg.write_frames(
            str(output_path),
            size=(even_w, even_h),
            fps=fps,
            pix_fmt_in="rgb24",
            pix_fmt_out="yuv420p",
            codec="libx264",
            macro_block_size=1,
        )
        expect_rgba = False

    writer.send(None)
    try:
        for i in range(total_frames):
            t = i / fps
            arr = animator.make_frame(t)
            if expect_rgba and arr.shape[2] == 3:
                img = Image.fromarray(arr).convert("RGBA")
                arr = img_to_arr(img)
            elif not expect_rgba and arr.shape[2] == 4:
                img = Image.fromarray(arr).convert("RGB")
                arr = img_to_arr(img)

            if fmt == "mp4" and (arr.shape[1] % 2 != 0 or arr.shape[0] % 2 != 0):
                arr = arr[: arr.shape[0] - (arr.shape[0] % 2), : arr.shape[1] - (arr.shape[1] % 2)]

            writer.send(arr.tobytes())
            pct = 15.0 + ((i + 1) / total_frames) * 80.0
            job_manager.update_job(job_id, progress=pct, message_key="status.encoding")
    finally:
        writer.close()


def img_to_arr(img: Image.Image) -> Any:
    import numpy as np

    return np.array(img)


def generate_scenario_media(req: ScenarioRequest, job_id: str) -> None:
    """Scenario to Movie 動画/アニメーションを生成し、JobManager を更新する。"""
    try:
        job_manager.update_job(job_id, status="running", progress=5.0, message_key="status.preparing")
        _, sc_renderer, sc_animator, sc_encoder = _ensure_scenario_modules()

        font_info = get_font_by_id(req.font_id) or get_default_font()
        config = _build_config(req, str(font_info.file_path))

        blocks = parse_text_to_blocks(req.text, req.alignment)
        layout_blocks, canvas_h = sc_renderer.compute_layout(blocks, config)

        first_line_static = bool(blocks) and bool(blocks[0].text.strip())
        animator = sc_animator.FlyinAnimator(
            layout_blocks,
            canvas_h,
            config,
            first_line_static=first_line_static,
        )

        job_manager.update_job(job_id, progress=12.0, message_key="status.rendering")

        actual_format = req.output_format
        if actual_format == "mp4" and animator.is_transparent:
            actual_format = "webm"

        out_path = job_manager.allocate_output_path("scenario", actual_format)

        if actual_format in ("gif", "apng"):
            _encode_image_sequence(animator, out_path, actual_format, config, sc_encoder, job_id)
        else:
            _encode_video_stream(animator, out_path, actual_format, config, job_id)

        job_manager.update_job(
            job_id,
            status="completed",
            progress=100.0,
            message_key="status.completed",
            output_filename=out_path.name,
            output_format=actual_format,
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
