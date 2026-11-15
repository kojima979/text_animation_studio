import { GIFEncoder, applyPalette, quantize } from "./vendor/gifenc.esm.js";
import { ensureFontLoaded } from "./fonts-registry.js";

function yieldFrame() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

function measureCanvas(lines, fontCss, fontSize, padding, cursor) {
  const probeCanvas = document.createElement("canvas");
  const ctx = probeCanvas.getContext("2d");
  ctx.font = fontCss;

  const rowHeight = Math.ceil(fontSize * 1.35);
  let maxWidth = 0;
  for (const line of lines) {
    if (line) {
      maxWidth = Math.max(maxWidth, ctx.measureText(line).width);
    }
  }
  const cursorWidth = cursor ? ctx.measureText(cursor).width : 0;
  const width = Math.max(16, Math.ceil(maxWidth + cursorWidth + padding * 2));
  const height = Math.max(16, Math.ceil(lines.length * rowHeight + padding * 2));
  return { width, height, rowHeight };
}

function drawTypingFrame(ctx, lines, charPos, showCursor, fontCss, color, bgColor, isTransparent, cursor, width, height, rowHeight, padding) {
  if (isTransparent) {
    ctx.clearRect(0, 0, width, height);
  } else {
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, width, height);
  }

  ctx.font = fontCss;
  ctx.fillStyle = color;
  ctx.textBaseline = "top";
  ctx.textAlign = "left";

  let remaining = charPos;
  let y = padding;

  for (const line of lines) {
    const lineLen = line.length;
    if (remaining > lineLen) {
      if (line) {
        ctx.fillText(line, padding, y);
      }
      remaining -= lineLen;
    } else {
      const typed = line.slice(0, remaining);
      if (typed) {
        ctx.fillText(typed, padding, y);
      }
      const cx = typed ? padding + ctx.measureText(typed).width : padding;
      if (showCursor && cursor) {
        ctx.fillText(cursor, cx, y);
      }
      break;
    }
    y += rowHeight;
  }
}

export async function generateTypingGif(params, onProgress) {
  onProgress(5, "status.preparing");
  const family = await ensureFontLoaded(params.font_id, params.font_size);
  const fontCss = `${params.font_size}px "${family}"`;

  const rawText = (params.text || "").replace(/\n+$/, "");
  const lines = rawText.split("\n");
  const totalChars = lines.reduce((sum, l) => sum + l.length, 0);

  const isTransparent = params.bgTransparent;
  const bgColor = params.background_color || "#000000";
  const { width, height, rowHeight } = measureCanvas(lines, fontCss, params.font_size, params.padding, params.cursor);

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });

  const gif = GIFEncoder();
  const repeat = params.loop ? 0 : -1;
  const totalFrames = (totalChars + 1) + (params.blink_count * 2) + 1;
  let frameIndex = 0;

  async function addFrame(pos, showCursor, delayMs) {
    drawTypingFrame(
      ctx,
      lines,
      pos,
      showCursor,
      fontCss,
      params.color,
      bgColor,
      isTransparent,
      params.cursor,
      width,
      height,
      rowHeight,
      params.padding
    );

    const imageData = ctx.getImageData(0, 0, width, height);
    const rgba = imageData.data;

    if (isTransparent) {
      const palette = quantize(rgba, 256, { format: "rgba4444", oneBitAlpha: true });
      const index = applyPalette(rgba, palette, "rgba4444");
      const transIdx = palette.findIndex((c) => c[3] === 0);
      gif.writeFrame(index, width, height, {
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
      gif.writeFrame(index, width, height, {
        palette,
        delay: delayMs,
        repeat,
        dispose: 2,
      });
    }

    frameIndex += 1;
    const pct = Math.min(95, 10 + (frameIndex / Math.max(1, totalFrames)) * 85);
    onProgress(Math.round(pct), "status.rendering");
    if (frameIndex % 4 === 0) {
      await yieldFrame();
    }
  }

  for (let pos = 0; pos <= totalChars; pos++) {
    await addFrame(pos, true, params.char_delay);
  }

  for (let b = 0; b < params.blink_count; b++) {
    await addFrame(totalChars, false, params.cursor_blink_interval);
    await addFrame(totalChars, true, params.cursor_blink_interval);
  }

  await addFrame(totalChars, false, params.end_delay);

  onProgress(98, "status.encoding");
  gif.finish();
  const blob = new Blob([gif.bytes()], { type: "image/gif" });
  onProgress(100, "status.completed");

  return {
    blob,
    format: "gif",
    filename: "typing.gif",
    size: blob.size,
  };
}
