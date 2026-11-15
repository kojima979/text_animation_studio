"""GitHub Pages 用静的サイト (docs/) の構成・整合性テスト。"""

from __future__ import annotations

import subprocess
from pathlib import Path

DOCS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "docs"


def test_docs_required_files_exist() -> None:
    required = [
        DOCS_DIR / "index.html",
        DOCS_DIR / "js" / "app.js",
        DOCS_DIR / "js" / "fonts-registry.js",
        DOCS_DIR / "js" / "typing-engine.js",
        DOCS_DIR / "js" / "credits-engine.js",
        DOCS_DIR / "js" / "vendor" / "gifenc.esm.js",
        DOCS_DIR / "js" / "vendor" / "gifenc-LICENSE.txt",
        DOCS_DIR / "fonts" / "DotGothic16-Regular.ttf",
        DOCS_DIR / "fonts" / "DotGothic16-OFL.txt",
        DOCS_DIR / "fonts" / "MPLUS1p-Regular.ttf",
        DOCS_DIR / "fonts" / "MPLUS1p-OFL.txt",
        DOCS_DIR / "fonts" / "ShipporiMincho-Regular.ttf",
        DOCS_DIR / "fonts" / "ShipporiMincho-OFL.txt",
    ]
    for path in required:
        assert path.exists(), f"Missing required file: {path}"


def test_docs_content_and_no_apng_mp4() -> None:
    html = (DOCS_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (DOCS_DIR / "js" / "app.js").read_text(encoding="utf-8")

    # APNG / MP4 が削除されていること
    assert 'value="apng"' not in html
    assert 'value="mp4"' not in html

    # GIF / WebM のみサポートされていること
    assert 'value="gif"' in html
    assert 'value="webm"' in html

    # 新タイトル・デフォルト色・日英UIが含まれること
    assert "Typing GIF" in app_js
    assert "Scroll Credits" in app_js
    assert "#00FF66" in app_js
    assert "ja:" in app_js and "en:" in app_js


def test_docs_js_syntax() -> None:
    js_files = [
        str(DOCS_DIR / "js" / "app.js"),
        str(DOCS_DIR / "js" / "fonts-registry.js"),
        str(DOCS_DIR / "js" / "typing-engine.js"),
        str(DOCS_DIR / "js" / "credits-engine.js"),
    ]
    proc = subprocess.run(["node", "--check", *js_files], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
