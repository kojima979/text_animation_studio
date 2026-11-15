"""フリーフォント管理およびライセンス情報レジストリ。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

FONTS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "fonts"


@dataclass(frozen=True)
class FontInfo:
    """管理対象フリーフォントのメタデータ。"""

    id: str
    name: str
    style_ja: str
    style_en: str
    filename: str
    license_name: str
    license_url: str
    copyright: str
    license_file: str
    source_url: str

    @property
    def file_path(self) -> Path:
        return FONTS_DIR / self.filename

    @property
    def license_file_path(self) -> Path:
        return FONTS_DIR / self.license_file


_FONT_REGISTRY: List[FontInfo] = [
    FontInfo(
        id="dotgothic16",
        name="DotGothic16",
        style_ja="レトロ・ドット絵風ゴシック",
        style_en="Retro Pixel Gothic",
        filename="DotGothic16-Regular.ttf",
        license_name="SIL Open Font License 1.1 (OFL-1.1)",
        license_url="https://scripts.sil.org/OFL",
        copyright="Copyright 2020 The DotGothic16 Project Authors",
        license_file="DotGothic16-OFL.txt",
        source_url="https://github.com/fontworks-fonts/DotGothic16",
    ),
    FontInfo(
        id="mplus1p",
        name="M PLUS 1p",
        style_ja="モダン・ゴシック体（サンセリフ）",
        style_en="Modern Sans-serif (Gothic)",
        filename="MPLUS1p-Regular.ttf",
        license_name="SIL Open Font License 1.1 (OFL-1.1)",
        license_url="https://scripts.sil.org/OFL",
        copyright="Copyright 2016 The M+ Project Authors",
        license_file="MPLUS1p-OFL.txt",
        source_url="https://github.com/google/fonts/tree/main/ofl/mplus1p",
    ),
    FontInfo(
        id="shippori-mincho",
        name="Shippori Mincho",
        style_ja="明朝体（セリフ）",
        style_en="Traditional Serif (Mincho)",
        filename="ShipporiMincho-Regular.ttf",
        license_name="SIL Open Font License 1.1 (OFL-1.1)",
        license_url="https://scripts.sil.org/OFL",
        copyright="Copyright 2021 The Shippori Mincho Project Authors",
        license_file="ShipporiMincho-OFL.txt",
        source_url="https://github.com/fontdasu/ShipporiMincho",
    ),
]

_FONT_MAP: Dict[str, FontInfo] = {f.id: f for f in _FONT_REGISTRY}


def list_available_fonts() -> List[FontInfo]:
    """ファイルが存在する利用可能なフリーフォント一覧を返す。"""
    return [f for f in _FONT_REGISTRY if f.file_path.exists()]


def get_font_by_id(font_id: str) -> Optional[FontInfo]:
    """IDからフォント情報を取得する。存在しない場合はNone。"""
    info = _FONT_MAP.get(font_id)
    if info and info.file_path.exists():
        return info
    return None


def get_default_font() -> FontInfo:
    """デフォルトのフリーフォントを返す。"""
    available = list_available_fonts()
    if not available:
        raise FileNotFoundError(f"利用可能なフォントが見つかりません: {FONTS_DIR}")
    return available[0]


def read_license_text(font_id: str) -> Optional[str]:
    """指定フォントのライセンス全文を読み込む。"""
    info = get_font_by_id(font_id)
    if info and info.license_file_path.exists():
        return info.license_file_path.read_text(encoding="utf-8")
    return None
