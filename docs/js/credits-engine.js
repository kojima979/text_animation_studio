import { GIFEncoder, applyPalette, quantize } from "./vendor/gifenc.esm.js";
import { ensureFontLoaded } from "./fonts-registry.js";

function yieldFrame() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

function createRng(seed = 42) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function uniform(rng, min, max) {
  return min + rng() * (max - min);
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function easeOutElastic(t, bounce) {
  const clamped = Math.max(0, Math.min(1, t));
  const smooth = clamped * clamped * (3 - 2 * clamped);
  const c4 = (2 * Math.PI) / 3;
  const elastic = Math.pow(2, -10 * clamped) * Math.sin((clamped * 10 - 0.75) * c4) + 1;
  return smooth * (1 - bounce) + elastic * bounce;
}

export function parseMarkdownScript(text, alignment) {
  const blocks = [];
  for (const rawLine of (text || "").split(/\r?\n/)) {
    const stripped = rawLine.trim();
    if (!stripped) {
      blocks.push({ text: "", headingLevel: 0, alignment });
    } else if (stripped.startsWith("## ")) {
      blocks.push({ text: stripped.slice(3).trim(), headingLevel: 2, alignment });
    } else if (stripped.startsWith("# ")) {
      blocks.push({ text: stripped.slice(2).trim(), headingLevel: 1, alignment });
    } else {
      blocks.push({ text: rawLine, headingLevel: 0, alignment });
    }
  }
  return blocks;
}

function wrapText(ctx, text, fontCss, maxWidth) {
  if (!text.trim()) return [];
  ctx.font = fontCss;
  const lines = [];
  let current = "";
  for (const ch of text) {
    const test = current + ch;
    if (ctx.measureText(test).width <= maxWidth) {
      current = test;
    } else {
      if (current) lines.push(current);
      current = ch;
    }
  }
  if (current) lines.push(current);
  return lines.length > 0 ? lines : [text];
}

function computeLayout(blocks, params, family, ctx) {
  const maxTextW = Math.max(100, params.width - 2 * params.margin_x);
  const layoutBlocks = [];
  let y = 20;

  for (const block of blocks) {
    if (!block.text.trim()) {
      y += params.empty_line_height;
      continue;
    }
    let fontSize = params.font_size_body;
    if (block.headingLevel === 1) fontSize = params.font_size_heading1;
    else if (block.headingLevel === 2) fontSize = params.font_size_heading2;

    const fontCss = `${fontSize}px "${family}"`;
    const lines = wrapText(ctx, block.text, fontCss, maxTextW);
    const lineHeight = Math.floor(fontSize * params.line_spacing);
    const totalHeight = lines.length * lineHeight + params.paragraph_spacing;

    layoutBlocks.push({
      lines,
      canvasY: y,
      lineHeight,
      fontSize,
      fontCss,
      alignment: block.alignment,
      totalHeight,
    });
    y += totalHeight;
  }

  return { layoutBlocks, canvasHeight: y + 20 };
}

class CreditsAnimator {
  constructor(layoutBlocks, params, family, ctx, firstLineStatic = true) {
    this.videoW = params.width;
    this.videoH = params.height;
    this.scrollSpeed = params.scroll_speed;
    this.leading = params.leading_seconds;
    this.trailing = params.trailing_seconds;
    this.flyinDuration = params.flyin_duration;
    this.bounce = params.flyin_bounce;
    this.landingY = this.videoH * params.landing_y_ratio;
    this.isTransparent = params.bgTransparent;
    this.bgColor = params.background_color || "#000000";
    this.fontColor = params.font_color || "#00FF66";
    this.marginX = params.margin_x;
    this.scaleMin = 0.3;
    this.scaleMax = 2.0;
    this.scaleMode = params.flyin_scale_mode || "random";
    this.scaleShrinkStart = 3.0;
    this.rotMax = params.flyin_rotation_max;
    this.wanderRadius = params.flyin_wander_radius;
    this.wanderFreqMin = 0.8;
    this.wanderFreqMax = 2.5;
    this.fontSizeFinal = params.font_size_final;
    this.fontCssFinal = `${this.fontSizeFinal}px "${family}"`;

    const rng = createRng(42);
    this.blockAnims = [];
    const allLineAnims = [];

    for (const lb of layoutBlocks) {
      const lineAnims = [];
      ctx.font = lb.fontCss;

      lb.lines.forEach((line, lineIdx) => {
        const lineCanvasY = lb.canvasY + lineIdx * lb.lineHeight;
        const elapsedEnd = (this.videoH + lineCanvasY - this.landingY) / this.scrollSpeed;
        const triggerElapsed = Math.max(0, elapsedEnd - this.flyinDuration);
        const triggerTime = this.leading + triggerElapsed;

        const textW = ctx.measureText(line).width;
        const textStartX = this.textStartX(lb.alignment, textW);
        const charParams = this.buildCharParams(ctx, line, textStartX, lb.fontCss, rng);

        const la = { lb, lineIdx, lineCanvasY, triggerTime, charParams };
        lineAnims.push(la);
        allLineAnims.push(la);
      });

      this.blockAnims.push({ lb, lineAnims });
    }

    this.lastLineAnim = allLineAnims.length > 0 ? allLineAnims[allLineAnims.length - 1] : null;
    const firstLa = allLineAnims.length > 0 ? allLineAnims[0] : null;
    this.firstLineAnim = firstLineStatic && firstLa && firstLa !== this.lastLineAnim ? firstLa : null;

    if (this.lastLineAnim) {
      const la = this.lastLineAnim;
      const line = la.lb.lines[la.lineIdx];
      ctx.font = this.fontCssFinal;
      const textW = ctx.measureText(line).width;
      const textStartX = this.textStartX(la.lb.alignment, textW);
      const updated = this.buildCharParams(ctx, line, textStartX, this.fontCssFinal, null, la.charParams);
      la.charParams = updated;
    }

    const lastCanvasY = this.lastLineAnim ? this.lastLineAnim.lineCanvasY : 0;
    this.yOffsetFinal = Math.max(0, this.videoH + lastCanvasY - this.landingY);

    const otherLines = allLineAnims.filter((la) => la !== this.lastLineAnim);
    let yOffsetAllClear = this.yOffsetFinal;
    if (otherLines.length > 0) {
      yOffsetAllClear = Math.max(
        ...otherLines.map((la) => this.videoH + la.lineCanvasY + la.lb.lineHeight)
      );
    }

    this.yOffsetScrollEnd = Math.max(this.yOffsetFinal, yOffsetAllClear);
    this.scrollDuration = this.scrollSpeed > 0 ? this.yOffsetScrollEnd / this.scrollSpeed : 0;
    this.totalDuration = Math.max(0.5, this.leading + this.scrollDuration + this.trailing);
  }

  textStartX(alignment, textW) {
    if (alignment === "right") return this.videoW - this.marginX - textW;
    if (alignment === "left") return this.marginX;
    return (this.videoW - textW) / 2;
  }

  buildCharParams(ctx, line, textStartX, fontCss, rng, reuseParams = null) {
    ctx.font = fontCss;
    const params = [];
    const chars = Array.from(line);
    for (let i = 0; i < chars.length; i++) {
      const prefix = chars.slice(0, i).join("");
      const prefixPlus = chars.slice(0, i + 1).join("");
      const wBefore = ctx.measureText(prefix).width;
      const wAfter = ctx.measureText(prefixPlus).width;
      const charW = wAfter - wBefore;
      const charLeftX = textStartX + wBefore;

      if (reuseParams && reuseParams[i]) {
        params.push({
          ...reuseParams[i],
          charLeftX,
          charW,
        });
      } else {
        const startScale =
          this.scaleMode === "shrink"
            ? this.scaleShrinkStart
            : uniform(rng, this.scaleMin, this.scaleMax);
        params.push({
          char: chars[i],
          charLeftX,
          charW,
          startX: uniform(rng, -this.videoW * 0.3, this.videoW * 1.3),
          startY: uniform(rng, -this.videoH * 0.3, this.videoH * 1.3),
          startScale,
          startAngle: uniform(rng, -this.rotMax, this.rotMax),
          wanderAmp: uniform(rng, this.wanderRadius * 0.5, this.wanderRadius),
          wanderFreq: uniform(rng, this.wanderFreqMin, this.wanderFreqMax),
          phaseX: uniform(rng, 0, Math.PI * 2),
          phaseY: uniform(rng, 0, Math.PI * 2),
          rotWander: uniform(rng, 20, 60),
        });
      }
    }
    return params;
  }

  renderFrame(ctx, t) {
    if (this.isTransparent) {
      ctx.clearRect(0, 0, this.videoW, this.videoH);
    } else {
      ctx.fillStyle = this.bgColor;
      ctx.fillRect(0, 0, this.videoW, this.videoH);
    }

    const inScroll = t >= this.leading;
    const yOffset = inScroll ? Math.min((t - this.leading) * this.scrollSpeed, this.yOffsetScrollEnd) : 0;

    for (const ba of this.blockAnims) {
      const lb = ba.lb;
      for (const la of ba.lineAnims) {
        const isLast = la === this.lastLineAnim;
        const isFirstStatic = la === this.firstLineAnim;
        const fontCss = isLast ? this.fontCssFinal : lb.fontCss;
        const fontSize = isLast ? this.fontSizeFinal : lb.fontSize;
        const lineText = lb.lines[la.lineIdx];

        if (isFirstStatic) {
          const centerTop = this.landingY - fontSize * 0.45;
          const naturalY = this.videoH + la.lineCanvasY - yOffset;
          const displayY = inScroll ? Math.min(centerTop, naturalY) : centerTop;
          if (displayY + lb.lineHeight >= 0) {
            ctx.save();
            ctx.font = fontCss;
            ctx.fillStyle = this.fontColor;
            ctx.textBaseline = "top";
            ctx.textAlign = "left";
            const x = this.textStartX(lb.alignment, ctx.measureText(lineText).width);
            ctx.fillText(lineText, x, displayY);
            ctx.restore();
          }
          continue;
        }

        if (!inScroll) continue;

        const flyElapsed = t - la.triggerTime;
        let finalCy = 0;

        if (isLast) {
          if (flyElapsed < 0) continue;
          if (flyElapsed >= this.flyinDuration) {
            ctx.save();
            ctx.font = fontCss;
            ctx.fillStyle = this.fontColor;
            ctx.textBaseline = "top";
            ctx.textAlign = "left";
            const x = this.textStartX(lb.alignment, ctx.measureText(lineText).width);
            ctx.fillText(lineText, x, this.landingY - fontSize * 0.45);
            ctx.restore();
            continue;
          }
          finalCy = this.landingY;
        } else {
          const lineScreenY = this.videoH + la.lineCanvasY - yOffset;
          if (lineScreenY + lb.lineHeight < 0 || lineScreenY > this.videoH) continue;
          if (flyElapsed < 0) continue;
          if (flyElapsed >= this.flyinDuration) {
            ctx.save();
            ctx.font = fontCss;
            ctx.fillStyle = this.fontColor;
            ctx.textBaseline = "top";
            ctx.textAlign = "left";
            const x = this.textStartX(lb.alignment, ctx.measureText(lineText).width);
            ctx.fillText(lineText, x, lineScreenY);
            ctx.restore();
            continue;
          }
          finalCy = lineScreenY + fontSize * 0.45;
        }

        const progress = flyElapsed / this.flyinDuration;
        const easeP = easeOutElastic(progress, this.bounce);
        const wanderDecay = Math.pow(Math.max(0, Math.min(1, 1 - easeP)), 1.5);
        const alpha = progress * progress * (3 - 2 * progress);

        ctx.save();
        ctx.font = fontCss;
        ctx.fillStyle = this.fontColor;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.globalAlpha = Math.max(0, Math.min(1, alpha));

        for (const cp of la.charParams) {
          const finalCx = cp.charLeftX + cp.charW / 2;
          const baseCx = lerp(cp.startX, finalCx, easeP);
          const baseCy = lerp(cp.startY, finalCy, easeP);

          const tau = Math.PI * 2 * cp.wanderFreq * flyElapsed;
          const wx = Math.sin(tau + cp.phaseX) * cp.wanderAmp * wanderDecay;
          const wy = Math.cos(tau * 1.3 + cp.phaseY) * cp.wanderAmp * 0.5 * wanderDecay;

          const cx = baseCx + wx;
          const cy = baseCy + wy;
          const scale = lerp(cp.startScale, 1.0, easeP);
          const angleDeg =
            lerp(cp.startAngle, 0.0, easeP) +
            Math.sin(tau * 0.7 + cp.phaseX + 1.0) * cp.rotWander * wanderDecay;

          ctx.save();
          ctx.translate(cx, cy);
          if (Math.abs(angleDeg) > 0.5) {
            ctx.rotate((angleDeg * Math.PI) / 180);
          }
          if (Math.abs(scale - 1.0) > 0.01) {
            ctx.scale(scale, scale);
          }
          ctx.fillText(cp.char, 0, 0);
          ctx.restore();
        }
        ctx.restore();
      }
    }
  }
}

async function encodeGifFromAnimator(animator, params, onProgress) {
  let fps = params.gif_fps;
  const scale = params.gif_scale;
  const newW = Math.max(16, Math.round(params.width * scale));
  const newH = Math.max(16, Math.round(params.height * scale));

  let totalFrames = Math.floor(animator.totalDuration * fps) + 1;
  if (params.gif_max_frames && totalFrames > params.gif_max_frames) {
    fps = (params.gif_max_frames - 1) / animator.totalDuration;
    totalFrames = params.gif_max_frames;
  }
  const delayMs = Math.max(10, Math.round(1000 / fps));

  const renderCanvas = document.createElement("canvas");
  renderCanvas.width = params.width;
  renderCanvas.height = params.height;
  const renderCtx = renderCanvas.getContext("2d");

  const outCanvas = document.createElement("canvas");
  outCanvas.width = newW;
  outCanvas.height = newH;
  const outCtx = outCanvas.getContext("2d", { willReadFrequently: true });

  const gif = GIFEncoder();
  const repeat = params.gif_loop === 0 ? 0 : -1;

  for (let i = 0; i < totalFrames; i++) {
    const t = i / fps;
    animator.renderFrame(renderCtx, t);

    outCtx.clearRect(0, 0, newW, newH);
    outCtx.drawImage(renderCanvas, 0, 0, newW, newH);

    const rgba = outCtx.getImageData(0, 0, newW, newH).data;
    if (animator.isTransparent) {
      const palette = quantize(rgba, 256, { format: "rgba4444", oneBitAlpha: true });
      const index = applyPalette(rgba, palette, "rgba4444");
      const transIdx = palette.findIndex((c) => c[3] === 0);
      gif.writeFrame(index, newW, newH, {
        palette,
        delay: delayMs,
        repeat,
        transparent: transIdx >= 0,
        transparentIndex: transIdx >= 0 ? transIdx : 0,
        dispose: 2,
      });
    } else {
      const palette = quantize(rgba, 256, { format: "rgb565" });
      const index = applyPalette(rgba, palette, "rgb565");
      gif.writeFrame(index, newW, newH, {
        palette,
        delay: delayMs,
        repeat,
        dispose: 2,
      });
    }

    const pct = Math.min(95, 12 + ((i + 1) / Math.max(1, totalFrames)) * 83);
    onProgress(Math.round(pct), "status.rendering");
    if (i % 2 === 0) {
      await yieldFrame();
    }
  }

  onProgress(98, "status.encoding");
  gif.finish();
  const blob = new Blob([gif.bytes()], { type: "image/gif" });
  onProgress(100, "status.completed");

  return {
    blob,
    format: "gif",
    filename: "scroll-credits.gif",
    size: blob.size,
  };
}

async function encodeWebmFromAnimator(animator, params, onProgress) {
  if (typeof MediaRecorder === "undefined") {
    throw new Error("MediaRecorder API is not supported in this browser.");
  }

  const mimeCandidates = [
    "video/webm;codecs=vp9",
    "video/webm;codecs=vp8",
    "video/webm",
  ];
  const mimeType = mimeCandidates.find((m) => MediaRecorder.isTypeSupported(m));
  if (!mimeType) {
    throw new Error("WebM recording is not supported in this browser.");
  }

  const canvas = document.createElement("canvas");
  canvas.width = params.width;
  canvas.height = params.height;
  const ctx = canvas.getContext("2d");

  const fps = params.fps;
  const stream = canvas.captureStream(fps);
  const recorder = new MediaRecorder(stream, {
    mimeType,
    videoBitsPerSecond: 4_000_000,
  });

  const chunks = [];
  recorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) chunks.push(e.data);
  };

  const stopped = new Promise((resolve) => {
    recorder.onstop = () => resolve();
  });

  animator.renderFrame(ctx, 0);
  recorder.start(100);

  const durationMs = animator.totalDuration * 1000;
  const startTime = performance.now();

  await new Promise((resolve) => {
    function step(now) {
      const elapsedMs = now - startTime;
      const t = Math.min(animator.totalDuration, elapsedMs / 1000);
      animator.renderFrame(ctx, t);
      const pct = Math.min(95, 12 + (t / animator.totalDuration) * 83);
      onProgress(Math.round(pct), "status.encoding");

      if (elapsedMs < durationMs) {
        requestAnimationFrame(step);
      } else {
        resolve();
      }
    }
    requestAnimationFrame(step);
  });

  recorder.stop();
  await stopped;

  const blob = new Blob(chunks, { type: "video/webm" });
  onProgress(100, "status.completed");

  return {
    blob,
    format: "webm",
    filename: "scroll-credits.webm",
    size: blob.size,
  };
}

export async function generateScrollCredits(params, onProgress) {
  onProgress(5, "status.preparing");
  const family = await ensureFontLoaded(params.font_id, params.font_size_body);

  const measureCanvas = document.createElement("canvas");
  const measureCtx = measureCanvas.getContext("2d");

  const blocks = parseMarkdownScript(params.text, params.alignment);
  const { layoutBlocks } = computeLayout(blocks, params, family, measureCtx);
  const firstLineStatic = blocks.length > 0 && Boolean(blocks[0].text.trim());

  const animator = new CreditsAnimator(layoutBlocks, params, family, measureCtx, firstLineStatic);

  onProgress(10, "status.rendering");
  if (params.output_format === "webm") {
    return encodeWebmFromAnimator(animator, params, onProgress);
  }
  return encodeGifFromAnimator(animator, params, onProgress);
}
