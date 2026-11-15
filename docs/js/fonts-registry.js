export const FONTS = [
  {
    id: "dotgothic16",
    name: "DotGothic16",
    family: "DotGothic16",
    style_ja: "レトロ・ドット絵風ゴシック",
    style_en: "Retro Pixel Gothic",
    file: "./fonts/DotGothic16-Regular.ttf",
    license_name: "SIL Open Font License 1.1 (OFL-1.1)",
    license_file: "./fonts/DotGothic16-OFL.txt",
    copyright: "Copyright 2020 The DotGothic16 Project Authors",
    source_url: "https://github.com/fontworks-fonts/DotGothic16",
    license_text: "",
  },
  {
    id: "mplus1p",
    name: "M PLUS 1p",
    family: "MPLUS1p",
    style_ja: "モダン・ゴシック体（サンセリフ）",
    style_en: "Modern Sans-serif (Gothic)",
    file: "./fonts/MPLUS1p-Regular.ttf",
    license_name: "SIL Open Font License 1.1 (OFL-1.1)",
    license_file: "./fonts/MPLUS1p-OFL.txt",
    copyright: "Copyright 2016 The M+ Project Authors",
    source_url: "https://github.com/google/fonts/tree/main/ofl/mplus1p",
    license_text: "",
  },
  {
    id: "shippori-mincho",
    name: "Shippori Mincho",
    family: "ShipporiMincho",
    style_ja: "明朝体（セリフ）",
    style_en: "Traditional Serif (Mincho)",
    file: "./fonts/ShipporiMincho-Regular.ttf",
    license_name: "SIL Open Font License 1.1 (OFL-1.1)",
    license_file: "./fonts/ShipporiMincho-OFL.txt",
    copyright: "Copyright 2021 The Shippori Mincho Project Authors",
    source_url: "https://github.com/fontdasu/ShipporiMincho",
    license_text: "",
  },
];

const loadedFonts = new Set();

export function getFontById(fontId) {
  return FONTS.find((f) => f.id === fontId) || FONTS[0];
}

export async function ensureFontLoaded(fontId, sizePx = 48) {
  const fontInfo = getFontById(fontId);
  if (!loadedFonts.has(fontInfo.id)) {
    const face = new FontFace(fontInfo.family, `url(${fontInfo.file})`);
    const loaded = await face.load();
    document.fonts.add(loaded);
    loadedFonts.add(fontInfo.id);
  }
  await document.fonts.load(`${sizePx}px "${fontInfo.family}"`);
  return fontInfo.family;
}

export async function loadAllLicenseTexts() {
  await Promise.all(
    FONTS.map(async (f) => {
      try {
        const res = await fetch(f.license_file);
        if (res.ok) {
          f.license_text = await res.text();
        }
      } catch {
        f.license_text = `${f.copyright}\nLicensed under ${f.license_name}`;
      }
    })
  );
}
