export const locales = ["hi", "en", "pa", "mr", "gu", "ur", "ta", "ml"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";
export const rtlLocales: ReadonlySet<string> = new Set(["ur"]);
export const LOCALE_COOKIE = "NEXT_LOCALE";

/** Native name first (shown on language tiles), English second (Part 1 §8.1). */
export const languageNames: Record<Locale, { native: string; english: string; greeting: string }> = {
  hi: { native: "हिन्दी", english: "Hindi", greeting: "नमस्ते! कारू में आपका स्वागत है।" },
  en: { native: "English", english: "English", greeting: "Hello! Welcome to Karu." },
  pa: { native: "ਪੰਜਾਬੀ", english: "Punjabi", greeting: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਕਾਰੂ ਵਿੱਚ ਜੀ ਆਇਆਂ ਨੂੰ।" },
  mr: { native: "मराठी", english: "Marathi", greeting: "नमस्कार! कारूमध्ये आपले स्वागत आहे." },
  gu: { native: "ગુજરાતી", english: "Gujarati", greeting: "નમસ્તે! કારુમાં આપનું સ્વાગત છે." },
  ur: { native: "اردو", english: "Urdu", greeting: "آداب! کارو میں خوش آمدید۔" },
  ta: { native: "தமிழ்", english: "Tamil", greeting: "வணக்கம்! காருவுக்கு வரவேற்கிறோம்." },
  ml: { native: "മലയാളം", english: "Malayalam", greeting: "നമസ്കാരം! കാരുവിലേക്ക് സ്വാഗതം." },
};

/** BCP-47 tags for Web Speech API recognition and speech synthesis. */
export const speechTags: Record<Locale, string> = {
  hi: "hi-IN", en: "en-IN", pa: "pa-IN", mr: "mr-IN", gu: "gu-IN", ur: "ur-IN", ta: "ta-IN", ml: "ml-IN",
};

export function isLocale(value: string | undefined | null): value is Locale {
  return !!value && (locales as readonly string[]).includes(value);
}

export function negotiate(acceptLanguage: string | null | undefined): Locale {
  for (const part of (acceptLanguage || "").split(",")) {
    const code = part.split(";")[0].trim().split("-")[0].toLowerCase();
    if (isLocale(code)) return code;
  }
  return defaultLocale;
}
