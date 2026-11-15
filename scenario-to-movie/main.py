"""scenario-to-movie: docx台本をフライイン×スクロール動画に変換する"""

import argparse
import sys
import yaml
from pathlib import Path

from docx_parser import parse_docx
from renderer import compute_layout
from animator import FlyinAnimator
from encoder import encode_video


def load_config(config_path: str) -> dict:
    defaults = {
        'background_color': '#000000',  # 'transparent' で透明背景（WebM出力）
        'font_color': '#FFFFFF',
        'font_path': '',
        'font_size_body': 36,
        'font_size_heading1': 56,
        'font_size_heading2': 46,
        'font_size_final': 80,
        'line_spacing': 1.8,
        'empty_line_height': 60,
        'paragraph_spacing': 20,
        'margin_x': 180,
        'resolution': [1920, 1080],
        'fps': 30,
        'scroll_speed': 120,
        'leading_seconds': 2,
        'trailing_seconds': 3,
        'flyin_duration': 1.8,
        'landing_y_ratio': 0.6,
        'flyin_bounce': 0.5,
        'flyin_rotation_max': 180,
        'flyin_alpha_start': 0,
        'flyin_scale_mode': 'random',
        'flyin_scale_min': 0.3,
        'flyin_scale_max': 2.0,
        'flyin_scale_shrink_start': 3.0,
        'gif_fps': 10,
        'gif_scale': 0.5,
        'gif_max_frames': None,
        'gif_loop': 0,
        'flyin_wander_radius': 400,
        'flyin_wander_freq_min': 0.8,
        'flyin_wander_freq_max': 2.5,
    }
    path = Path(config_path)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            user = yaml.safe_load(f) or {}
        defaults.update(user)
    return defaults


def main():
    parser = argparse.ArgumentParser(
        description='docx台本をフライイン×スクロール動画（MP4）に変換します'
    )
    parser.add_argument('input', help='入力 .docx ファイル')
    parser.add_argument('-o', '--output', default='output.mp4', help='出力 MP4 ファイル（デフォルト: output.mp4）')
    parser.add_argument('-c', '--config', default='config.yaml', help='設定ファイル（デフォルト: config.yaml）')
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f'エラー: ファイルが見つかりません: {args.input}', file=sys.stderr)
        sys.exit(1)

    print(f'設定読み込み: {args.config}')
    config = load_config(args.config)

    print(f'テキスト解析: {args.input}')
    blocks = parse_docx(args.input)
    print(f'  段落数: {len(blocks)}')

    print('レイアウト計算中...')
    layout_blocks, canvas_h = compute_layout(blocks, config)
    print(f'  テキストブロック数: {len(layout_blocks)}, キャンバス高さ: {canvas_h}px')

    print('アニメーター初期化...')
    first_line_static = bool(blocks) and bool(blocks[0].text.strip())
    animator = FlyinAnimator(layout_blocks, canvas_h, config, first_line_static=first_line_static)
    print(f'  総再生時間: {animator.total_duration:.1f}秒')

    print(f'動画エンコード中 → {args.output}')
    encode_video(animator, args.output, config)


if __name__ == '__main__':
    main()
