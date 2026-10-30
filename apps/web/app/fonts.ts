import {
  Fraunces,
  Noto_Naskh_Arabic,
  Noto_Nastaliq_Urdu,
  Noto_Sans,
  Noto_Sans_Devanagari,
  Noto_Sans_Gujarati,
  Noto_Sans_Gurmukhi,
  Noto_Sans_Malayalam,
  Noto_Sans_Tamil,
  Noto_Serif_Devanagari,
} from "next/font/google";

// Display: Fraunces (+ Noto Serif Devanagari, Nastaliq for Urdu). UI: Noto Sans per script; Urdu UI in
// Naskh (Nastaliq is too tall for dense UI) — Part 1 §9.3. Script fonts are not preloaded: with
// unicode-range subsets the browser only downloads the scripts a page actually renders.
// next/font options must be written as literals (they are analysed at build time).

export const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces", display: "swap" });
export const notoSans = Noto_Sans({ subsets: ["latin"], variable: "--font-noto-sans", display: "swap" });
export const deva = Noto_Sans_Devanagari({ subsets: ["devanagari"], weight: ["400", "500", "600", "700"], variable: "--font-noto-sans-devanagari", display: "swap", preload: false });
export const devaSerif = Noto_Serif_Devanagari({ subsets: ["devanagari"], weight: ["500", "600"], variable: "--font-noto-serif-devanagari", display: "swap", preload: false });
export const gurmukhi = Noto_Sans_Gurmukhi({ subsets: ["gurmukhi"], weight: ["400", "500", "600", "700"], variable: "--font-noto-sans-gurmukhi", display: "swap", preload: false });
export const gujarati = Noto_Sans_Gujarati({ subsets: ["gujarati"], weight: ["400", "500", "600", "700"], variable: "--font-noto-sans-gujarati", display: "swap", preload: false });
export const tamil = Noto_Sans_Tamil({ subsets: ["tamil"], weight: ["400", "500", "600", "700"], variable: "--font-noto-sans-tamil", display: "swap", preload: false });
export const malayalam = Noto_Sans_Malayalam({ subsets: ["malayalam"], weight: ["400", "500", "600", "700"], variable: "--font-noto-sans-malayalam", display: "swap", preload: false });
export const naskh = Noto_Naskh_Arabic({ subsets: ["arabic"], weight: ["400", "500", "600", "700"], variable: "--font-naskh", display: "swap", preload: false });
export const nastaliq = Noto_Nastaliq_Urdu({ subsets: ["arabic"], weight: ["400", "600"], variable: "--font-nastaliq", display: "swap", preload: false });

export const fontVariables = [fraunces, notoSans, deva, devaSerif, gurmukhi, gujarati, tamil, malayalam, naskh, nastaliq]
  .map((f) => f.variable)
  .join(" ");
