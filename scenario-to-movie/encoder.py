"""アニメーターのフレームをMP4 / WebM / APNG / GIF にエンコードする"""

from pathlib import Path
import numpy as np
from PIL import Image
from moviepy import VideoClip


def encode_video(animator, output_path: str, config: dict) -> None:
    ext = Path(output_path).suffix.lower()
    if ext == '.gif':
        _encode_gif(animator, output_path, config)
    elif ext in ('.apng', '.png'):
        _encode_apng(animator, output_path, config)
    elif animator.is_transparent:
        _encode_webm_rgba(animator, output_path, config)
    else:
        _encode_mp4_rgb(animator, output_path, config)


# ── MP4（不透明）────────────────────────────────────────────────────────────

def _encode_mp4_rgb(animator, output_path: str, config: dict) -> None:
    fps = config['fps']
    clip = VideoClip(animator.make_frame, duration=animator.total_duration)
    clip.write_videofile(output_path, fps=fps, codec='libx264', audio=False, logger=None)
    print(f'出力完了: {output_path}')


# ── WebM VP9 + alpha ─────────────────────────────────────────────────────────

def _encode_webm_rgba(animator, output_path: str, config: dict) -> None:
    import imageio_ffmpeg

    fps = config['fps']
    video_w, video_h = config['resolution']

    out_path = Path(output_path)
    if out_path.suffix.lower() != '.webm':
        out_path = out_path.with_suffix('.webm')
        print(f'  背景透明のため出力形式を WebM に変更: {out_path}')

    total_frames = int(animator.total_duration * fps) + 1
    writer = imageio_ffmpeg.write_frames(
        str(out_path), size=(video_w, video_h), fps=fps,
        pix_fmt_in='rgba', pix_fmt_out='yuva420p', codec='libvpx-vp9',
        macro_block_size=1, output_params=['-b:v', '0', '-crf', '30'],
    )
    writer.send(None)
    for i in range(total_frames):
        t = i / fps
        writer.send(animator.make_frame(t).tobytes())
        if i % (fps * 5) == 0:
            print(f'  エンコード中... {t:.1f}s / {animator.total_duration:.1f}s')
    writer.close()
    print(f'出力完了: {out_path}')


# ── フレーム数制限ヘルパー ──────────────────────────────────────────────────

def _clamp_frames(fps: float, duration: float, max_frames) -> tuple:
    """gif_max_frames を超える場合は fps を下げてフレーム数を制限する"""
    total = int(duration * fps) + 1
    if max_frames and total > max_frames:
        fps = (max_frames - 1) / duration
        total = max_frames
        print(f'  gif_max_frames={max_frames} に合わせて fps を {fps:.2f} に調整')
    return fps, total


# ── APNG（PowerPoint / Google Slides 透明対応）──────────────────────────────

def _encode_apng(animator, output_path: str, config: dict) -> None:
    fps    = config.get('gif_fps', 10)
    scale  = config.get('gif_scale', 0.5)
    video_w, video_h = config['resolution']
    new_w = max(1, int(video_w * scale))
    new_h = max(1, int(video_h * scale))
    fps, total_frames = _clamp_frames(fps, animator.total_duration, config.get('gif_max_frames'))
    duration_ms = int(1000 / fps)

    out_path = Path(output_path)
    if out_path.suffix.lower() not in ('.apng', '.png'):
        out_path = out_path.with_suffix('.apng')

    print(f'  APNG: {new_w}x{new_h} @ {fps}fps, {total_frames}フレーム → {out_path}')

    frames = []
    for i in range(total_frames):
        t = i / fps
        arr = animator.make_frame(t)   # RGBA または RGB
        img = Image.fromarray(arr)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        if scale != 1.0:
            img = img.resize((new_w, new_h), Image.LANCZOS)
        frames.append(img)
        if i % (fps * 5) == 0:
            print(f'  フレーム生成中... {t:.1f}s / {animator.total_duration:.1f}s')

    loop = config.get('gif_loop', 0)
    frames[0].save(
        str(out_path),
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=loop,
    )
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f'出力完了: {out_path}  ({size_mb:.1f} MB)')


# ── GIF（最大互換・バイナリ透明）────────────────────────────────────────────

def _encode_gif(animator, output_path: str, config: dict) -> None:
    fps   = config.get('gif_fps', 10)
    scale = config.get('gif_scale', 0.5)
    video_w, video_h = config['resolution']
    new_w = max(1, int(video_w * scale))
    new_h = max(1, int(video_h * scale))
    fps, total_frames = _clamp_frames(fps, animator.total_duration, config.get('gif_max_frames'))
    duration_ms = int(1000 / fps)

    print(f'  GIF: {new_w}x{new_h} @ {fps}fps, {total_frames}フレーム → {output_path}')

    frames = []
    for i in range(total_frames):
        t = i / fps
        arr = animator.make_frame(t)
        img = Image.fromarray(arr)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        if scale != 1.0:
            img = img.resize((new_w, new_h), Image.LANCZOS)

        # RGBA → パレット変換（透明インデックス付き）
        gif_frame = _rgba_to_gif_palette(img)
        frames.append(gif_frame)
        if i % (fps * 5) == 0:
            print(f'  フレーム生成中... {t:.1f}s / {animator.total_duration:.1f}s')

    loop = config.get('gif_loop', 0)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=loop,
        transparency=0,
        disposal=2,
    )
    size_mb = Path(output_path).stat().st_size / 1024 / 1024
    print(f'出力完了: {output_path}  ({size_mb:.1f} MB)')


def _rgba_to_gif_palette(rgba_img: Image.Image) -> Image.Image:
    """RGBA画像をGIF用パレット画像（透明インデックス=0）に変換する"""
    alpha = np.array(rgba_img.split()[3])

    # 不透明部分だけ RGB で量子化（255色）
    rgb = rgba_img.convert('RGB')
    quantized = rgb.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=0)
    palette = quantized.getpalette()  # 255色 × 3 = 765要素

    # インデックス0を透明色として予約（黒: 0,0,0 を先頭に追加）
    new_palette = [0, 0, 0] + palette[:255 * 3]  # 256色分
    p_arr = np.array(quantized, dtype=np.uint8) + 1  # 既存インデックスを1〜255にシフト
    p_arr[alpha < 128] = 0  # 半透明以下のピクセルを透明インデックスへ

    result = Image.fromarray(p_arr, mode='P')
    result.putpalette(new_palette)
    return result
