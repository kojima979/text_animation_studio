# scenario-to-movie

docx形式の台本を、映画エンドクレジット風のスクロール動画に変換するツール。
MP4 / WebM（透明背景）/ APNG / GIF に対応。

---

## 特徴

- `.docx` ファイルを読み込み、見出し・本文のスタイルを自動解析
- 各行のテキストが画面外からランダムに飛び込み、回転・拡縮・バウンス・漂いながら着地
- 着地後はそのままスクロールに乗って上へ流れる映画クレジット風演出
- 背景透明（WebM / APNG / GIF）に対応、PowerPoint・Google Slides への貼り付けに利用可能
- すべての挙動を YAML で設定可能

---

## アニメーション仕様

### コンセプト

スクロールは止まらず連続して進む。各行テキストは、画面内の着地位置に差し掛かる直前にランダム方向から飛び込んでくる。文字は自由に漂いながら（Lissajous 軌道）収束し、バウンスしながら着地する。着地後はスクロールに乗ってそのまま上へ流れていく。

### アニメーションフロー

```
時間 ──────────────────────────────────────────────→

[リーディング]  [スクロール開始]
  空白           ↓
                 1行目が着地位置に近づく → 各文字がバラバラに飛び込む
                        ↓ flyin_duration 秒で着地
                 スクロール継続（1行目は上に流れていく）
                        ↓
                 2行目が着地位置に近づく → 飛び込む
                        ...繰り返し
                                            [トレイリング]
                                              空白
```

### 1行あたりのライフサイクル

| フェーズ | 状態 | 描画 |
|---|---|---|
| 未登場 | 着地時刻まで未到達 | 描画しない |
| フライイン中 | `trigger_time` から `flyin_duration` 秒間 | 文字ごとにアニメーション描画 |
| 着地済み | `flyin_duration` 秒経過後 | 最終座標に静止描画（スクロールで上へ） |

### 文字ごとのフライインパラメータ

| パラメータ | 内容 |
|---|---|
| `start_pos` | 画面内外のランダムな座標 |
| `start_scale` | `flyin_scale_min`〜`flyin_scale_max` 倍（randomモード）または `flyin_scale_shrink_start` 倍（shrinkモード） |
| `start_angle` | `-flyin_rotation_max`°〜`+flyin_rotation_max`° |
| `wander_amp` | `flyin_wander_radius` × 0.5〜1.0 |
| `wander_freq` | `flyin_wander_freq_min`〜`flyin_wander_freq_max` Hz |
| easing | easeOutElastic（`flyin_bounce` でバウンス強度調整） |

---

## ファイル構成

```
scenario-to-movie/
├── main.py              # エントリーポイント・フロー制御
├── docx_parser.py       # docx読み込み・段落構造解析
├── renderer.py          # レイアウト座標計算
├── animator.py          # フライインパラメータ生成・イージング・フレーム描画
├── encoder.py           # frame-by-frameエンコード → 各形式出力
├── config.yaml          # 設定ファイル
├── requirements.txt     # 依存パッケージ
└── create_test_docx.py  # テスト用docx生成スクリプト
```

---

## 使い方

```bash
python main.py input.docx -o output.gif -c config.yaml
```

| 引数 | 説明 | デフォルト |
|---|---|---|
| `input` | 入力 .docx ファイル | （必須） |
| `-o` / `--output` | 出力ファイル（拡張子で形式自動判定） | `output.mp4` |
| `-c` / `--config` | 設定ファイル | `config.yaml` |

### 出力形式

拡張子によって自動的に出力形式が切り替わります。

| 拡張子 | 形式 | 透明背景 | 用途 |
|---|---|---|---|
| `.mp4` | MP4 (H.264) | 不可 | 動画配信・一般用途 |
| `.webm` | WebM (VP9) | 可 | Web埋め込み |
| `.gif` | GIF | 可（2値） | PowerPoint / Google Slides |
| `.apng` / `.png` | APNG | 可 | PowerPoint / Google Slides |

`background_color: "transparent"` のとき MP4 を指定すると自動的に WebM に切り替わります。

---

## 設定ファイル（config.yaml）

### 画面・フォント

| パラメータ | 説明 | デフォルト |
|---|---|---|
| `background_color` | 背景色（`"transparent"` で透明） | `"#000000"` |
| `font_color` | 文字色 | `"#FFFFFF"` |
| `font_path` | フォントファイルパス（TTF/OTF/TTC）。空欄でシステム自動検出 | `""` |
| `font_size_body` | 本文フォントサイズ（px） | `36` |
| `font_size_heading1` | 見出し1フォントサイズ（px） | `56` |
| `font_size_heading2` | 見出し2フォントサイズ（px） | `46` |
| `line_spacing` | 行間倍率 | `1.8` |
| `empty_line_height` | 空行の高さ（px） | `60` |
| `paragraph_spacing` | 段落間の余白（px） | `20` |
| `margin_x` | 左右余白（px） | `180` |

### 動画

| パラメータ | 説明 | デフォルト |
|---|---|---|
| `resolution` | 解像度 `[幅, 高さ]` | `[1920, 1080]` |
| `fps` | フレームレート（MP4 / WebM） | `30` |
| `scroll_speed` | スクロール速度（px/秒） | `120` |
| `leading_seconds` | 開始前の空白時間（秒） | `2` |
| `trailing_seconds` | 終了後の空白時間（秒） | `3` |

### フライインアニメーション

| パラメータ | 説明 | デフォルト |
|---|---|---|
| `flyin_duration` | 1行のフライイン時間（秒） | `1.8` |
| `landing_y_ratio` | 着地Y位置（0.0=上端、0.5=中央、1.0=下端） | `0.6` |
| `flyin_bounce` | バウンス強度（0=なし、1=強） | `0.5` |
| `flyin_rotation_max` | 最大初期回転角（度） | `180` |
| `flyin_alpha_start` | 出現時の透明度（0=完全透明、255=不透明） | `0` |
| `flyin_scale_mode` | スケールモード（`random` または `shrink`） | `"random"` |
| `flyin_scale_min` | 最小初期スケール（randomモード） | `0.3` |
| `flyin_scale_max` | 最大初期スケール（randomモード） | `2.0` |
| `flyin_scale_shrink_start` | 初期スケール倍率（shrinkモード） | `3.0` |
| `flyin_wander_radius` | 漂い半径（px） | `400` |
| `flyin_wander_freq_min` | 漂い周波数の最小値（Hz） | `0.8` |
| `flyin_wander_freq_max` | 漂い周波数の最大値（Hz） | `2.5` |

**`flyin_scale_mode` の違い:**

- `random` — 文字ごとにランダムなスケールで登場し、1.0 に収束
- `shrink` — 全文字が `flyin_scale_shrink_start` 倍の大きさで登場し、1.0 に収束

### GIF / APNG

| パラメータ | 説明 | デフォルト |
|---|---|---|
| `gif_fps` | GIF / APNG のフレームレート | `10` |
| `gif_scale` | 解像度倍率（1.0 = resolution そのまま） | `0.5` |
| `gif_max_frames` | フレーム数上限（超えた場合は fps を自動調整）。`null` で無制限 | `null` |
| `gif_loop` | ループ回数（`0` = 無限ループ、`1` = 1回再生して最終フレームで停止） | `0` |

**`gif_loop` の使い方:**

```yaml
gif_loop: 0   # 無限ループ（デフォルト）
gif_loop: 1   # 1回だけ再生し、最後のフレームで静止
```

Google Slides でアニメーションを1回だけ流して静止させたい場合は `gif_loop: 1` を設定します。

---

## docxファイルの書き方

| Wordスタイル | 用途 | フォントサイズ |
|---|---|---|
| 見出し1 | タイトル・大見出し | `font_size_heading1` |
| 見出し2 | 中見出し | `font_size_heading2` |
| 標準（本文） | 本文テキスト | `font_size_body` |
| 空行 | 行間スペース | `empty_line_height` |

テキストの配置（左・中央・右）はWord側の段落設定を引き継ぎます。

---

## 依存パッケージ

```
python-docx
pillow
moviepy
numpy
PyYAML
imageio-ffmpeg
```

インストール:

```bash
pip install -r requirements.txt
```

---

## テスト

テスト用docx（スティーブ・ジョブズ スタンフォード卒業スピーチ 日本語）を生成:

```bash
python create_test_docx.py
python main.py test_speech.docx -o output.gif
```
