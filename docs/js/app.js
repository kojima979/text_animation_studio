import { FONTS, loadAllLicenseTexts } from "./fonts-registry.js";
import { generateTypingGif } from "./typing-engine.js";
import { generateScrollCredits } from "./credits-engine.js";

const I18N = {
  ja: {
    appTitle: "Text Animation Studio",
    appSubtitle: "Typing GIF & Scroll Credits ジェネレーター（ブラウザ完結版）",
    tabTypewriter: "Typing GIF",
    tabScenario: "Scroll Credits",
    licenseBtn: "フォント・ライセンス情報",
    inputSectionTitle: "テキスト入力",
    typewriterTextLabel: "アニメーションするテキスト",
    typewriterTextHint: "改行すると複数行として描画されます。",
    scenarioTextLabel: "台本テキスト（直接入力）",
    scenarioTextHint: "# 見出し1 / ## 見出し2 / 空行でスペース / 通常行は本文として扱われます。",
    alignmentLabel: "テキスト配置",
    alignCenter: "中央寄せ (center)",
    alignLeft: "左寄せ (left)",
    alignRight: "右寄せ (right)",
    settingsBasic: "基本設定",
    settingsAdvanced: "詳細パラメータ",
    fontLabel: "使用フォント（フリーライセンス）",
    fontSizeLabel: "フォントサイズ (px)",
    textColorLabel: "文字色",
    bgColorLabel: "背景色",
    bgTransparent: "透明 (Transparent)",
    charDelayLabel: "1文字の間隔 (ms)",
    cursorCharLabel: "カーソル文字",
    blinkIntervalLabel: "カーソル点滅間隔 (ms)",
    blinkCountLabel: "終了後点滅回数",
    endDelayLabel: "最終停止時間 (ms)",
    paddingLabel: "余白 Padding (px)",
    loopLabel: "無限ループ再生",
    outputFormatLabel: "出力形式",
    webmRealtimeNote: "※ WebM 出力はブラウザ標準の録画機能を用いるため、アニメーションの実再生時間と同等の処理時間がかかります。",
    resolutionLabel: "解像度",
    fpsLabel: "フレームレート (FPS)",
    scrollSpeedLabel: "スクロール速度 (px/秒)",
    leadingSecondsLabel: "開始前空白 (秒)",
    trailingSecondsLabel: "終了後空白 (秒)",
    fontSizeBodyLabel: "本文サイズ (px)",
    fontSizeH1Label: "見出し1 サイズ (px)",
    fontSizeH2Label: "見出し2 サイズ (px)",
    fontSizeFinalLabel: "最終行サイズ (px)",
    flyinDurationLabel: "フライイン時間 (秒)",
    landingYRatioLabel: "着地Y位置 (比率)",
    flyinBounceLabel: "バウンス強度",
    flyinRotationMaxLabel: "最大初期回転角 (度)",
    flyinScaleModeLabel: "スケールモード",
    scaleModeRandom: "ランダム (random)",
    scaleModeShrink: "縮小 (shrink)",
    flyinWanderRadiusLabel: "漂い半径 (px)",
    gifFpsLabel: "GIF FPS",
    gifScaleLabel: "GIF 解像度倍率",
    gifMaxFramesLabel: "最大フレーム数上限",
    gifLoopLabel: "GIF ループ",
    gifLoopInfinite: "無限ループ (0)",
    gifLoopOnce: "1回再生して停止 (1)",
    generateBtn: "アニメーションを生成",
    generatingBtn: "生成中...",
    previewTitle: "プレビュー & ダウンロード",
    previewEmpty: "左側のパラメータを設定して「アニメーションを生成」を押してください。",
    previewBgLabel: "プレビュー背景:",
    previewBgChecker: "透過チェック",
    previewBgDark: "ダーク",
    previewBgLight: "ライト",
    downloadBtn: "ファイルをダウンロード",
    fileInfoFormat: "形式",
    fileInfoSize: "サイズ",
    resetBtn: "初期値に戻す",
    loadSampleBtn: "サンプル文を入力",
    footerLicenseTitle: "使用フリーフォント・ライセンス表記",
    footerLicenseDesc: "本Webアプリでは権利関係の安全性を確保するため、以下の SIL Open Font License 1.1 (OFL-1.1) 準拠フォントのみを使用しています。すべての処理はお使いのブラウザ内で完結します。",
    viewLicenseText: "ライセンス全文を見る",
    closeBtn: "閉じる",
    status: {
      preparing: "フォントとレイアウトを準備中...",
      rendering: "フレームを描画中...",
      encoding: "メディアをエンコード中...",
      completed: "生成が完了しました！",
      failed: "生成中にエラーが発生しました",
    },
  },
  en: {
    appTitle: "Text Animation Studio",
    appSubtitle: "Typing GIF & Scroll Credits Generator (Client-Side)",
    tabTypewriter: "Typing GIF",
    tabScenario: "Scroll Credits",
    licenseBtn: "Fonts & Licenses",
    inputSectionTitle: "Text Input",
    typewriterTextLabel: "Text to Animate",
    typewriterTextHint: "Line breaks create multiple lines.",
    scenarioTextLabel: "Script Text (Direct Input)",
    scenarioTextHint: "Use # Heading 1, ## Heading 2, blank lines for spacing, and plain lines for body text.",
    alignmentLabel: "Text Alignment",
    alignCenter: "Center",
    alignLeft: "Left",
    alignRight: "Right",
    settingsBasic: "Basic Settings",
    settingsAdvanced: "Advanced Parameters",
    fontLabel: "Font (Open Source License)",
    fontSizeLabel: "Font Size (px)",
    textColorLabel: "Text Color",
    bgColorLabel: "Background",
    bgTransparent: "Transparent",
    charDelayLabel: "Char Delay (ms)",
    cursorCharLabel: "Cursor Symbol",
    blinkIntervalLabel: "Cursor Blink Interval (ms)",
    blinkCountLabel: "Blink Count After Typing",
    endDelayLabel: "End Hold Delay (ms)",
    paddingLabel: "Padding (px)",
    loopLabel: "Infinite Loop",
    outputFormatLabel: "Output Format",
    webmRealtimeNote: "Note: WebM recording runs via browser MediaRecorder in real time matching the animation duration.",
    resolutionLabel: "Resolution",
    fpsLabel: "Frame Rate (FPS)",
    scrollSpeedLabel: "Scroll Speed (px/s)",
    leadingSecondsLabel: "Leading Blank (sec)",
    trailingSecondsLabel: "Trailing Blank (sec)",
    fontSizeBodyLabel: "Body Font Size (px)",
    fontSizeH1Label: "Heading 1 Size (px)",
    fontSizeH2Label: "Heading 2 Size (px)",
    fontSizeFinalLabel: "Final Line Size (px)",
    flyinDurationLabel: "Fly-in Duration (sec)",
    landingYRatioLabel: "Landing Y Ratio",
    flyinBounceLabel: "Bounce Strength",
    flyinRotationMaxLabel: "Max Initial Rotation (deg)",
    flyinScaleModeLabel: "Scale Mode",
    scaleModeRandom: "Random",
    scaleModeShrink: "Shrink",
    flyinWanderRadiusLabel: "Wander Radius (px)",
    gifFpsLabel: "GIF FPS",
    gifScaleLabel: "GIF Scale",
    gifMaxFramesLabel: "Max Frames Limit",
    gifLoopLabel: "GIF Loop",
    gifLoopInfinite: "Infinite (0)",
    gifLoopOnce: "Play Once & Stop (1)",
    generateBtn: "Generate Animation",
    generatingBtn: "Generating...",
    previewTitle: "Preview & Download",
    previewEmpty: "Configure your text and parameters on the left, then click Generate Animation.",
    previewBgLabel: "Preview BG:",
    previewBgChecker: "Checker",
    previewBgDark: "Dark",
    previewBgLight: "Light",
    downloadBtn: "Download File",
    fileInfoFormat: "Format",
    fileInfoSize: "Size",
    resetBtn: "Reset Defaults",
    loadSampleBtn: "Load Sample",
    footerLicenseTitle: "Bundled Free Fonts & Licenses",
    footerLicenseDesc: "To ensure clear usage rights, this web app exclusively uses the following SIL Open Font License 1.1 (OFL-1.1) fonts. All rendering runs locally in your browser.",
    viewLicenseText: "View Full License",
    closeBtn: "Close",
    status: {
      preparing: "Preparing fonts and layout...",
      rendering: "Rendering frames...",
      encoding: "Encoding media...",
      completed: "Generation completed!",
      failed: "An error occurred during generation",
    },
  },
};

const SAMPLES = {
  ja: {
    typewriter: "こんにちは、世界！\n文字がカタカタ打たれるGIFです。",
    scenario: "# Text Animation Studio\n\n## 新たなる物語の幕開け\n\n一文字ずつ画面外から舞い降りて\nやがてひとつの文章になる。\n\nFIN",
  },
  en: {
    typewriter: "Hello, World!\nTyping animation GIF.",
    scenario: "# Text Animation Studio\n\n## A New Story Begins\n\nEach character flies in from afar\nand lands gracefully in place.\n\nTHE END",
  },
};

function defaultTw(lang) {
  return {
    text: SAMPLES[lang].typewriter,
    font_id: "dotgothic16",
    font_size: 48,
    color: "#00FF66",
    bgTransparent: true,
    background_color: "#000000",
    char_delay: 80,
    cursor_blink_interval: 500,
    blink_count: 3,
    end_delay: 2000,
    padding: 20,
    loop: false,
    cursor: "▌",
  };
}

function defaultSc(lang) {
  return {
    text: SAMPLES[lang].scenario,
    alignment: "center",
    output_format: "gif",
    font_id: "dotgothic16",
    bgTransparent: true,
    background_color: "#000000",
    font_color: "#00FF66",
    resolutionPreset: "1280x720",
    width: 1280,
    height: 720,
    fps: 24,
    scroll_speed: 90,
    leading_seconds: 0.5,
    trailing_seconds: 3.0,
    font_size_body: 36,
    font_size_heading1: 56,
    font_size_heading2: 46,
    font_size_final: 80,
    flyin_duration: 1.6,
    landing_y_ratio: 0.5,
    flyin_bounce: 0.5,
    flyin_rotation_max: 180,
    flyin_scale_mode: "random",
    flyin_wander_radius: 350,
    margin_x: 120,
    line_spacing: 1.8,
    empty_line_height: 60,
    paragraph_spacing: 20,
    gif_fps: 15,
    gif_scale: 0.6,
    gif_max_frames: 300,
    gif_loop: 0,
  };
}

function animationApp() {
  return {
    lang: "ja",
    activeTab: "typewriter",
    showAdvanced: false,
    fonts: FONTS,
    licenseModalFont: null,
    previewBg: "checker",
    isGenerating: false,
    progress: 0,
    statusKey: "",
    errorMessage: "",
    result: null,
    objectUrl: null,

    tw: defaultTw("ja"),
    sc: defaultSc("ja"),

    async init() {
      const savedLang = localStorage.getItem("tas_lang");
      if (savedLang === "ja" || savedLang === "en") {
        this.lang = savedLang;
      } else if (navigator.language && !navigator.language.startsWith("ja")) {
        this.lang = "en";
      }
      this.tw.text = SAMPLES[this.lang].typewriter;
      this.sc.text = SAMPLES[this.lang].scenario;
      await loadAllLicenseTexts();
    },

    setLang(newLang) {
      this.lang = newLang;
      localStorage.setItem("tas_lang", newLang);
    },

    t(key) {
      const parts = key.split(".");
      let cur = I18N[this.lang];
      for (const p of parts) {
        if (cur && Object.prototype.hasOwnProperty.call(cur, p)) {
          cur = cur[p];
        } else {
          return key;
        }
      }
      return cur;
    },

    loadSample() {
      if (this.activeTab === "typewriter") {
        this.tw.text = SAMPLES[this.lang].typewriter;
      } else {
        this.sc.text = SAMPLES[this.lang].scenario;
      }
    },

    resetDefaults() {
      if (this.activeTab === "typewriter") {
        this.tw = defaultTw(this.lang);
      } else {
        this.sc = defaultSc(this.lang);
      }
    },

    applyResolutionPreset() {
      const [w, h] = this.sc.resolutionPreset.split("x").map(Number);
      this.sc.width = w;
      this.sc.height = h;
    },

    formatBytes(bytes) {
      if (!bytes) return "0 B";
      const k = 1024;
      const sizes = ["B", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    },

    async generate() {
      if (this.isGenerating) return;
      if (this.objectUrl) {
        URL.revokeObjectURL(this.objectUrl);
        this.objectUrl = null;
      }

      this.isGenerating = true;
      this.progress = 0;
      this.statusKey = "status.preparing";
      this.errorMessage = "";
      this.result = null;

      try {
        const onProgress = (pct, key) => {
          this.progress = pct;
          this.statusKey = key;
        };

        const out =
          this.activeTab === "typewriter"
            ? await generateTypingGif(this.tw, onProgress)
            : await generateScrollCredits(this.sc, onProgress);

        this.objectUrl = URL.createObjectURL(out.blob);
        this.result = {
          output_url: this.objectUrl,
          download_url: this.objectUrl,
          output_filename: out.filename,
          output_format: out.format,
          file_size_bytes: out.size,
        };
      } catch (err) {
        this.statusKey = "status.failed";
        this.errorMessage = err?.message || String(err);
      } finally {
        this.isGenerating = false;
      }
    },
  };
}

document.addEventListener("alpine:init", () => {
  window.Alpine.data("animationApp", animationApp);
});
