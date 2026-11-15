"""API リクエスト・レスポンス用 Pydantic スキーマ定義。"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


def _validate_hex_color(v: str, allow_transparent: bool = False) -> str:
    cleaned = v.strip()
    if allow_transparent and cleaned.lower() == "transparent":
        return "transparent"
    if not cleaned.startswith("#") or len(cleaned) != 7:
        raise ValueError("カラーコードは #RRGGBB 形式で指定してください")
    try:
        int(cleaned[1:], 16)
    except ValueError as exc:
        raise ValueError("カラーコードは16進数で指定してください") from exc
    return cleaned.upper()


class FontItemResponse(BaseModel):
    """フォント情報レスポンス。"""

    id: str
    name: str
    style_ja: str
    style_en: str
    license_name: str
    license_url: str
    copyright: str
    source_url: str
    license_text: Optional[str] = None


class TypewriterRequest(BaseModel):
    """Typewriter GIF 生成リクエスト。"""

    text: str = Field(..., min_length=1, max_length=2000)
    font_id: str = Field(default="dotgothic16")
    font_size: int = Field(default=48, ge=12, le=200)
    color: str = Field(default="#00FF66")
    background_color: str = Field(default="transparent")
    char_delay: int = Field(default=80, ge=10, le=2000)
    cursor_blink_interval: int = Field(default=500, ge=50, le=3000)
    blink_count: int = Field(default=3, ge=0, le=20)
    end_delay: int = Field(default=2000, ge=0, le=10000)
    padding: int = Field(default=20, ge=0, le=200)
    loop: bool = Field(default=False)
    cursor: str = Field(default="▌", min_length=0, max_length=5)

    @field_validator("color")
    @classmethod
    def check_color(cls, v: str) -> str:
        return _validate_hex_color(v, allow_transparent=False)

    @field_validator("background_color")
    @classmethod
    def check_bg_color(cls, v: str) -> str:
        return _validate_hex_color(v, allow_transparent=True)


class ScenarioRequest(BaseModel):
    """Scenario to Movie 生成リクエスト。"""

    text: str = Field(..., min_length=1, max_length=10000)
    alignment: Literal["center", "left", "right"] = Field(default="center")
    output_format: Literal["gif", "apng", "mp4", "webm"] = Field(default="gif")

    # フォント・色設定
    font_id: str = Field(default="dotgothic16")
    background_color: str = Field(default="transparent")
    font_color: str = Field(default="#00FF66")
    font_size_body: int = Field(default=36, ge=12, le=160)
    font_size_heading1: int = Field(default=56, ge=16, le=200)
    font_size_heading2: int = Field(default=46, ge=14, le=180)
    font_size_final: int = Field(default=80, ge=16, le=240)
    line_spacing: float = Field(default=1.8, ge=1.0, le=4.0)
    empty_line_height: int = Field(default=60, ge=10, le=300)
    paragraph_spacing: int = Field(default=20, ge=0, le=200)
    margin_x: int = Field(default=120, ge=0, le=600)

    # 動画・スクロール設定
    width: int = Field(default=1280, ge=320, le=1920)
    height: int = Field(default=720, ge=240, le=1080)
    fps: int = Field(default=24, ge=5, le=60)
    scroll_speed: int = Field(default=90, ge=10, le=500)
    leading_seconds: float = Field(default=0.5, ge=0.0, le=10.0)
    trailing_seconds: float = Field(default=3.0, ge=0.0, le=30.0)

    # フライインアニメーション設定
    flyin_duration: float = Field(default=1.6, ge=0.2, le=5.0)
    landing_y_ratio: float = Field(default=0.5, ge=0.1, le=0.9)
    flyin_bounce: float = Field(default=0.5, ge=0.0, le=1.0)
    flyin_rotation_max: int = Field(default=180, ge=0, le=360)
    flyin_alpha_start: int = Field(default=0, ge=0, le=255)
    flyin_scale_mode: Literal["random", "shrink"] = Field(default="random")
    flyin_scale_min: float = Field(default=0.3, ge=0.1, le=5.0)
    flyin_scale_max: float = Field(default=2.0, ge=0.1, le=5.0)
    flyin_scale_shrink_start: float = Field(default=3.0, ge=1.0, le=6.0)
    flyin_wander_radius: int = Field(default=350, ge=0, le=1000)
    flyin_wander_freq_min: float = Field(default=0.8, ge=0.1, le=5.0)
    flyin_wander_freq_max: float = Field(default=2.5, ge=0.1, le=8.0)

    # GIF / APNG 設定
    gif_fps: int = Field(default=15, ge=5, le=30)
    gif_scale: float = Field(default=0.6, ge=0.2, le=1.0)
    gif_max_frames: int = Field(default=300, ge=30, le=1500)
    gif_loop: int = Field(default=0, ge=0, le=1)

    @field_validator("font_color")
    @classmethod
    def check_font_color(cls, v: str) -> str:
        return _validate_hex_color(v, allow_transparent=False)

    @field_validator("background_color")
    @classmethod
    def check_bg_color(cls, v: str) -> str:
        return _validate_hex_color(v, allow_transparent=True)


class JobCreatedResponse(BaseModel):
    """ジョブ生成レスポンス。"""

    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    """ジョブ進捗レスポンス。"""

    job_id: str
    status: str
    progress: float
    message_key: str
    output_url: Optional[str] = None
    download_url: Optional[str] = None
    output_filename: Optional[str] = None
    output_format: Optional[str] = None
    file_size_bytes: int = 0
    error_detail: Optional[str] = None
