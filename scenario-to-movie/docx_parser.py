"""docxファイルを読み込み、段落構造を解析する"""

from dataclasses import dataclass
from typing import List
from docx import Document


@dataclass
class TextBlock:
    text: str
    heading_level: int  # 0=本文, 1=見出し1, 2=見出し2, ...
    alignment: str      # 'center', 'left', 'right'


def parse_docx(path: str) -> List[TextBlock]:
    doc = Document(path)
    blocks = []
    for para in doc.paragraphs:
        text = para.text
        style_name = para.style.name.lower()

        heading_level = 0
        if 'heading' in style_name or '見出し' in style_name:
            try:
                heading_level = int(style_name.split()[-1])
            except ValueError:
                heading_level = 1

        align = _get_alignment(para)
        blocks.append(TextBlock(text=text, heading_level=heading_level, alignment=align))

    return blocks


def _get_alignment(para) -> str:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    a = para.alignment
    if a == WD_ALIGN_PARAGRAPH.CENTER:
        return 'center'
    if a == WD_ALIGN_PARAGRAPH.RIGHT:
        return 'right'
    return 'center'  # スタッフロールはデフォルト中央寄せ
