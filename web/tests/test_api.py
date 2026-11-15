"""Webアプリケーション統合・単体テスト。"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.storage import job_manager
from app.main import app
from app.services.scenario_service import parse_text_to_blocks

client = TestClient(app)


def _wait_job_completion(job_id: str, timeout_sec: float = 30.0) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        res = client.get(f"/api/jobs/{job_id}")
        assert res.status_code == 200
        data = res.json()
        if data["status"] in ("completed", "failed"):
            return data
        time.sleep(0.1)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout_sec}s")


def test_index_page() -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert "Text Animation Studio" in res.text
    assert "app.js" in res.text

    js_res = client.get("/static/js/app.js")
    assert js_res.status_code == 200
    assert "Typing GIF" in js_res.text
    assert "Scroll Credits" in js_res.text
    assert "#00FF66" in js_res.text


def test_fonts_endpoint_and_licenses() -> None:
    res = client.get("/api/fonts?include_license_text=true")
    assert res.status_code == 200
    fonts = res.json()
    assert len(fonts) == 3
    ids = {f["id"] for f in fonts}
    assert ids == {"dotgothic16", "mplus1p", "shippori-mincho"}
    for f in fonts:
        assert "SIL Open Font License 1.1" in f["license_name"]
        assert "SIL OPEN FONT LICENSE" in f["license_text"]


def test_parse_text_to_blocks() -> None:
    sample = "# 大見出し\n\n## 小見出し\n本文テキスト"
    blocks = parse_text_to_blocks(sample, "left")
    assert len(blocks) == 4
    assert (blocks[0].text, blocks[0].heading_level, blocks[0].alignment) == ("大見出し", 1, "left")
    assert (blocks[1].text, blocks[1].heading_level) == ("", 0)
    assert (blocks[2].text, blocks[2].heading_level) == ("小見出し", 2)
    assert (blocks[3].text, blocks[3].heading_level) == ("本文テキスト", 0)


@pytest.mark.parametrize("bg_color", ["transparent", "#112233"])
def test_typewriter_generate_gif(bg_color: str) -> None:
    payload = {
        "text": "テスト\nOK",
        "font_id": "dotgothic16",
        "font_size": 24,
        "color": "#FFFFFF",
        "background_color": bg_color,
        "char_delay": 50,
        "cursor_blink_interval": 100,
        "blink_count": 1,
        "end_delay": 200,
        "padding": 10,
        "loop": False,
        "cursor": "|",
    }
    res = client.post("/api/typewriter/generate", json=payload)
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    data = _wait_job_completion(job_id)
    assert data["status"] == "completed", data.get("error_detail")
    assert data["output_format"] == "gif"
    assert data["file_size_bytes"] > 0

    out_res = client.get(data["output_url"])
    assert out_res.status_code == 200
    assert out_res.headers["content-type"] == "image/gif"

    dl_res = client.get(data["download_url"])
    assert dl_res.status_code == 200

    out_path = job_manager.get_output_path(data["output_filename"])
    assert out_path is not None
    with Image.open(out_path) as img:
        assert img.format == "GIF"
        assert getattr(img, "is_animated", False) is True


@pytest.mark.parametrize(
    "fmt,bg,expected_fmt",
    [
        ("gif", "transparent", "gif"),
        ("apng", "transparent", "apng"),
        ("mp4", "#000000", "mp4"),
        ("mp4", "transparent", "webm"),  # transparent時は自動的にWebMへ切替
        ("webm", "transparent", "webm"),
    ],
)
def test_scenario_generate_formats(fmt: str, bg: str, expected_fmt: str) -> None:
    payload = {
        "text": "# Title\nHello",
        "alignment": "center",
        "output_format": fmt,
        "font_id": "mplus1p",
        "background_color": bg,
        "font_color": "#FFFFFF",
        "width": 320,
        "height": 240,
        "fps": 10,
        "scroll_speed": 150,
        "leading_seconds": 0.0,
        "trailing_seconds": 0.5,
        "flyin_duration": 0.4,
        "gif_fps": 10,
        "gif_scale": 0.5,
        "gif_max_frames": 30,
        "gif_loop": 1,
    }
    res = client.post("/api/scenario/generate", json=payload)
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    data = _wait_job_completion(job_id, timeout_sec=45.0)
    assert data["status"] == "completed", data.get("error_detail")
    assert data["output_format"] == expected_fmt
    assert data["file_size_bytes"] > 0

    out_res = client.get(data["output_url"])
    assert out_res.status_code == 200


def test_validation_and_security() -> None:
    # 無効なカラーコード
    bad = client.post("/api/typewriter/generate", json={"text": "hi", "color": "red"})
    assert bad.status_code == 422

    # 存在しないファイルへのアクセス
    missing = client.get("/api/outputs/nonexistent_file.gif")
    assert missing.status_code == 404
