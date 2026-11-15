"""フライイン×スクロール連動アニメーション（文字が自由に動き回って集合）"""

import math
import random
from dataclasses import dataclass
from typing import List

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from renderer import LayoutBlock, _parse_color, _load_font


def _ease_out_elastic(t: float, bounce: float) -> float:
    t = max(0.0, min(1.0, t))
    smooth = t * t * (3 - 2 * t)
    c4 = (2 * math.pi) / 3
    elastic = math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1
    return smooth * (1 - bounce) + elastic * bounce


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@dataclass
class CharParam:
    char: str
    char_left_x: int
    char_w: float
    # 散乱開始位置（画面内外ランダム）
    start_x: float
    start_y: float
    start_scale: float
    start_angle: float
    # 漂い運動パラメータ
    wander_amp: float    # 漂い半径（px）
    wander_freq: float   # 漂い周波数（Hz）
    phase_x: float       # X方向の位相
    phase_y: float       # Y方向の位相（Xと独立させることでランダム軌跡）
    rot_wander: float    # 漂い中の回転ゆらぎ（度）


@dataclass
class LineAnim:
    lb: LayoutBlock          # フォント・整列などブロック情報を共有
    line_idx: int            # ブロック内の行インデックス
    line_canvas_y: int       # この行のキャンバスY座標
    trigger_time: float
    char_params: List[CharParam]


@dataclass
class BlockAnim:
    lb: LayoutBlock
    line_anims: List[LineAnim]


class FlyinAnimator:
    def __init__(self, layout_blocks: List[LayoutBlock], canvas_h: int, config: dict,
                 first_line_static: bool = True):
        self.config = config
        video_w, video_h = config['resolution']
        self.video_w = video_w
        self.video_h = video_h
        self.scroll_speed = config['scroll_speed']
        self.leading = config['leading_seconds']
        self.trailing = config['trailing_seconds']
        self.flyin_duration = config.get('flyin_duration', 1.8)
        self.bounce = config.get('flyin_bounce', 0.5)
        landing_y_ratio = config.get('landing_y_ratio', 0.6)
        self.landing_y = video_h * landing_y_ratio
        bg_cfg = str(config.get('background_color', '#000000'))
        if bg_cfg.lower() == 'transparent':
            self.is_transparent = True
            self.bg_color = (0, 0, 0, 0)   # RGBA: 完全透明
        else:
            self.is_transparent = False
            self.bg_color = _parse_color(bg_cfg)
        self.font_color = _parse_color(config['font_color'])
        self.margin_x = config['margin_x']
        self.scale_min = config.get('flyin_scale_min', 0.3)
        self.scale_max = config.get('flyin_scale_max', 2.0)
        self.scale_mode = config.get('flyin_scale_mode', 'random')       # 'random' | 'shrink'
        self.scale_shrink_start = config.get('flyin_scale_shrink_start', 3.0)
        self.rot_max = config.get('flyin_rotation_max', 180)
        self.alpha_start = int(config.get('flyin_alpha_start', 0))       # 0=完全透明 〜 255=不透明
        self.wander_radius = config.get('flyin_wander_radius', 400)
        self.wander_freq_min = config.get('flyin_wander_freq_min', 0.8)
        self.wander_freq_max = config.get('flyin_wander_freq_max', 2.5)

        size_final = config.get('font_size_final', config.get('font_size_heading1', 56))
        self.font_final = _load_font(config.get('font_path', ''), size_final)
        self.font_size_final = size_final

        rng = random.Random(42)
        self.block_anims: List[BlockAnim] = []

        tmp_img = Image.new('RGB', (1, 1))
        measure = ImageDraw.Draw(tmp_img)

        for lb in layout_blocks:
            line_anims = []
            for line_idx, line in enumerate(lb.lines):
                # 行ごとに canvas_y と trigger_time を独立計算
                line_canvas_y = lb.canvas_y + line_idx * lb.line_height
                elapsed_end = (video_h + line_canvas_y - self.landing_y) / self.scroll_speed
                trigger_elapsed = max(0.0, elapsed_end - self.flyin_duration)
                trigger_time = self.leading + trigger_elapsed

                text_w = measure.textlength(line, font=lb.font)
                text_start_x = self._text_start_x(lb.alignment, int(text_w))

                char_params = []
                for i, char in enumerate(line):
                    w_before = measure.textlength(line[:i], font=lb.font)
                    w_after = measure.textlength(line[:i + 1], font=lb.font)
                    char_w = w_after - w_before
                    char_left_x = text_start_x + int(w_before)

                    start_x = rng.uniform(-video_w * 0.3, video_w * 1.3)
                    start_y = rng.uniform(-video_h * 0.3, video_h * 1.3)

                    if self.scale_mode == 'shrink':
                        start_scale = self.scale_shrink_start
                    else:
                        start_scale = rng.uniform(self.scale_min, self.scale_max)

                    char_params.append(CharParam(
                        char=char,
                        char_left_x=char_left_x,
                        char_w=char_w,
                        start_x=start_x,
                        start_y=start_y,
                        start_scale=start_scale,
                        start_angle=rng.uniform(-self.rot_max, self.rot_max),
                        wander_amp=rng.uniform(self.wander_radius * 0.5, self.wander_radius),
                        wander_freq=rng.uniform(self.wander_freq_min, self.wander_freq_max),
                        phase_x=rng.uniform(0, math.tau),
                        phase_y=rng.uniform(0, math.tau),
                        rot_wander=rng.uniform(20, 60),
                    ))

                line_anims.append(LineAnim(
                    lb=lb,
                    line_idx=line_idx,
                    line_canvas_y=line_canvas_y,
                    trigger_time=trigger_time,
                    char_params=char_params,
                ))

            self.block_anims.append(BlockAnim(lb=lb, line_anims=line_anims))

        # 最終行・最初行を特定する
        all_line_anims = [la for ba in self.block_anims for la in ba.line_anims]
        self.last_line_anim = all_line_anims[-1] if all_line_anims else None
        first_la = all_line_anims[0] if all_line_anims else None
        # 最初行が最終行と同じ（1行しかない）場合は静的表示しない
        self.first_line_anim = (
            first_la
            if first_line_static and first_la is not None and first_la is not self.last_line_anim
            else None
        )

        if self.last_line_anim is not None:
            la = self.last_line_anim
            line = la.lb.lines[la.line_idx]
            text_w = measure.textlength(line, font=self.font_final)
            text_start_x = self._text_start_x(la.lb.alignment, int(text_w))
            new_params = []
            for i, old_cp in enumerate(la.char_params):
                w_before = measure.textlength(line[:i], font=self.font_final)
                w_after = measure.textlength(line[:i + 1], font=self.font_final)
                new_params.append(CharParam(
                    char=old_cp.char,
                    char_left_x=text_start_x + int(w_before),
                    char_w=w_after - w_before,
                    start_x=old_cp.start_x,
                    start_y=old_cp.start_y,
                    start_scale=old_cp.start_scale,
                    start_angle=old_cp.start_angle,
                    wander_amp=old_cp.wander_amp,
                    wander_freq=old_cp.wander_freq,
                    phase_x=old_cp.phase_x,
                    phase_y=old_cp.phase_y,
                    rot_wander=old_cp.rot_wander,
                ))
            la.char_params = new_params

        # 最終行が landing_y に到達する y_offset
        last_canvas_y = self.last_line_anim.line_canvas_y if self.last_line_anim else 0
        self.y_offset_final = max(0.0, video_h + last_canvas_y - self.landing_y)

        # 最終行以外が画面上端を抜ける y_offset（これ以降は最終行だけが残る）
        other_lines = [la for la in all_line_anims if la is not self.last_line_anim]
        if other_lines:
            lb_map = {id(la): ba.lb for ba in self.block_anims for la in ba.line_anims}
            y_offset_all_clear = max(
                video_h + la.line_canvas_y + lb_map[id(la)].line_height
                for la in other_lines
            )
        else:
            y_offset_all_clear = self.y_offset_final
        self.y_offset_scroll_end = max(self.y_offset_final, y_offset_all_clear)

        self.scroll_duration = self.y_offset_scroll_end / self.scroll_speed if self.scroll_speed > 0 else 0
        self.total_duration = self.leading + self.scroll_duration + self.trailing

    def _text_start_x(self, alignment: str, text_w: int) -> int:
        if alignment == 'right':
            return self.video_w - self.margin_x - text_w
        if alignment == 'left':
            return self.margin_x
        return (self.video_w - text_w) // 2

    def _render_char_anim(self, frame: Image.Image, char: str,
                          font: ImageFont.FreeTypeFont, font_size: int,
                          cx: float, cy: float, scale: float, angle: float,
                          alpha: int = 255) -> None:
        s = int(font_size * 2.5)
        tmp = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text(
            (s // 2, s // 2), char, font=font, anchor='mm',
            fill=(*self.font_color, alpha)
        )
        if abs(scale - 1.0) > 0.01:
            new_s = max(1, int(s * scale))
            tmp = tmp.resize((new_s, new_s), Image.LANCZOS)
        if abs(angle) > 0.5:
            tmp = tmp.rotate(-angle, expand=True, resample=Image.BICUBIC)
        frame.paste(tmp, (int(cx - tmp.width / 2), int(cy - tmp.height / 2)), tmp)

    def make_frame(self, t: float) -> np.ndarray:
        mode = 'RGBA' if self.is_transparent else 'RGB'
        frame = Image.new(mode, (self.video_w, self.video_h), self.bg_color)
        draw = ImageDraw.Draw(frame)

        in_scroll = t >= self.leading
        if in_scroll:
            elapsed = t - self.leading
            y_offset = min(elapsed * self.scroll_speed, self.y_offset_scroll_end)
        else:
            y_offset = 0.0

        for ba in self.block_anims:
            lb = ba.lb
            for la in ba.line_anims:
                is_last = (la is self.last_line_anim)
                is_first_static = (la is self.first_line_anim)
                font = self.font_final if is_last else lb.font
                font_size = self.font_size_final if is_last else lb.font_size
                line_text = lb.lines[la.line_idx]

                if is_first_static:
                    # 最初行: 最初から画面中央に表示。スクロールで自然に上へ流れる
                    center_top = int(self.landing_y - font_size * 0.45)
                    if in_scroll:
                        natural_y = int(self.video_h + la.line_canvas_y - y_offset)
                        display_y = min(center_top, natural_y)
                    else:
                        display_y = center_top
                    if display_y + lb.line_height >= 0:
                        text_w = draw.textlength(line_text, font=font)
                        x = self._text_start_x(lb.alignment, int(text_w))
                        draw.text((x, display_y), line_text, font=font, fill=self.font_color)
                    continue

                if not in_scroll:
                    continue

                fly_elapsed = t - la.trigger_time

                if is_last:
                    # 最終行: フライイン後 landing_y に固定
                    if fly_elapsed < 0:
                        continue
                    if fly_elapsed >= self.flyin_duration:
                        text_w = draw.textlength(line_text, font=font)
                        x = self._text_start_x(lb.alignment, int(text_w))
                        draw.text((x, int(self.landing_y - font_size * 0.45)),
                                  line_text, font=font, fill=self.font_color)
                        continue
                    final_cy = self.landing_y
                else:
                    # 通常行: スクロールで上端を超えたら非表示
                    line_screen_y = int(self.video_h + la.line_canvas_y - y_offset)
                    if line_screen_y + lb.line_height < 0 or line_screen_y > self.video_h:
                        continue
                    if fly_elapsed < 0:
                        continue
                    if fly_elapsed >= self.flyin_duration:
                        text_w = draw.textlength(line_text, font=font)
                        x = self._text_start_x(lb.alignment, int(text_w))
                        draw.text((x, line_screen_y), line_text, font=font, fill=self.font_color)
                        continue
                    final_cy = line_screen_y + font_size * 0.45

                # 自由飛行 → 収束アニメーション
                progress = fly_elapsed / self.flyin_duration
                ease_p = _ease_out_elastic(progress, self.bounce)
                wander_decay = max(0.0, min(1.0, 1.0 - ease_p)) ** 1.5
                alpha_t = progress * progress * (3 - 2 * progress)
                alpha = int(_lerp(self.alpha_start, 255, alpha_t))

                for cp in la.char_params:
                    final_cx = cp.char_left_x + cp.char_w / 2
                    base_cx = _lerp(cp.start_x, final_cx, ease_p)
                    base_cy = _lerp(cp.start_y, final_cy, ease_p)

                    tau = math.tau * cp.wander_freq * fly_elapsed
                    wx = math.sin(tau + cp.phase_x) * cp.wander_amp * wander_decay
                    wy = math.cos(tau * 1.3 + cp.phase_y) * cp.wander_amp * 0.5 * wander_decay

                    cx = base_cx + wx
                    cy = base_cy + wy
                    scale = _lerp(cp.start_scale, 1.0, ease_p)
                    angle = _lerp(cp.start_angle, 0.0, ease_p) + \
                            math.sin(tau * 0.7 + cp.phase_x + 1.0) * cp.rot_wander * wander_decay

                    self._render_char_anim(
                        frame, cp.char, font, font_size,
                        cx, cy, scale, angle, alpha
                    )

        return np.array(frame)
