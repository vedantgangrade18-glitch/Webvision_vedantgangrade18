/** ₹1,00,000 grouping with Western digits in every language (Part 1 §8.1). */
export function inr(amount: number | null | undefined, opts: { decimals?: boolean } = {}): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "—";
  const fixed = opts.decimals || amount % 1 !== 0 ? 2 : 0;
  return "₹" + amount.toLocaleString("en-IN", { minimumFractionDigits: fixed, maximumFractionDigits: fixed });
}

const MONTHS: Record<string, string[]> = {
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
  hi: ["जन॰", "फ़र॰", "मार्च", "अप्रैल", "मई", "जून", "जुल॰", "अग॰", "सित॰", "अक्तू॰", "नव॰", "दिस॰"],
  pa: ["ਜਨ", "ਫ਼ਰ", "ਮਾਰਚ", "ਅਪ੍ਰੈ", "ਮਈ", "ਜੂਨ", "ਜੁਲਾ", "ਅਗ", "ਸਤੰ", "ਅਕਤੂ", "ਨਵੰ", "ਦਸੰ"],
  mr: ["जाने", "फेब्रु", "मार्च", "एप्रि", "मे", "जून", "जुलै", "ऑग", "सप्टें", "ऑक्टो", "नोव्हें", "डिसें"],
  gu: ["જાન્યુ", "ફેબ્રુ", "માર્ચ", "એપ્રિલ", "મે", "જૂન", "જુલાઈ", "ઑગસ્ટ", "સપ્ટે", "ઑક્ટો", "નવે", "ડિસે"],
  ur: ["جنوری", "فروری", "مارچ", "اپریل", "مئی", "جون", "جولائی", "اگست", "ستمبر", "اکتوبر", "نومبر", "دسمبر"],
  ta: ["ஜன.", "பிப்.", "மார்.", "ஏப்.", "மே", "ஜூன்", "ஜூலை", "ஆக.", "செப்.", "அக்.", "நவ.", "டிச."],
  ml: ["ജനു", "ഫെബ്രു", "മാർ", "ഏപ്രി", "മേയ്", "ജൂൺ", "ജൂലൈ", "ഓഗ", "സെപ്റ്റം", "ഒക്ടോ", "നവം", "ഡിസം"],
};

/** "24 Oct 2026" style, localised month, Western digits, IST. */
export function date(value: string | Date | null | undefined, locale = "en"): string {
  if (!value) return "";
  const d = typeof value === "string" ? new Date(value) : value;
  const ist = new Date(d.getTime() + (330 + d.getTimezoneOffset()) * 60000);
  const months = MONTHS[locale] || MONTHS.en;
  return `${ist.getDate()} ${months[ist.getMonth()]} ${ist.getFullYear()}`;
}

export function timeAgo(value: string | null | undefined, t: (key: string, values?: Record<string, number>) => string): string {
  if (!value) return "";
  const mins = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60000));
  if (mins < 60) return t("time.minutes", { n: Math.max(1, mins) });
  const hours = Math.round(mins / 60);
  if (hours < 48) return t("time.hours", { n: hours });
  return t("time.days", { n: Math.round(hours / 24) });
}

/** Approximate conversion for international visitors; Karu always charges INR (Part 1 §4.2). */
export const APPROX_RATES: Record<string, number> = { USD: 0.012, EUR: 0.011, GBP: 0.0094, AED: 0.044 };

export function approx(amountInr: number | null | undefined, currency: string): string | null {
  if (!amountInr || currency === "INR" || !APPROX_RATES[currency]) return null;
  const v = amountInr * APPROX_RATES[currency];
  return "≈ " + v.toLocaleString("en-US", { style: "currency", currency, maximumFractionDigits: 0 });
}

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}
