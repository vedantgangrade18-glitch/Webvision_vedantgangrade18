"""Server-side localisation: INR/date formatting and the small catalogue of strings the API
itself sends (verification tips, price advice, notifications, share captions).
UI strings live in the web app (`apps/web/messages`)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

LOCALES = ["hi", "en", "pa", "mr", "gu", "ur", "ta", "ml"]
RTL_LOCALES = {"ur"}
DEFAULT_LOCALE = "en"
IST = ZoneInfo("Asia/Kolkata")

LANGUAGE_NAMES = {
    "hi": "हिन्दी", "en": "English", "pa": "ਪੰਜਾਬੀ", "mr": "मराठी",
    "gu": "ગુજરાતી", "ur": "اردو", "ta": "தமிழ்", "ml": "മലയാളം",
}
LANGUAGE_NAMES_EN = {
    "hi": "Hindi", "en": "English", "pa": "Punjabi", "mr": "Marathi",
    "gu": "Gujarati", "ur": "Urdu", "ta": "Tamil", "ml": "Malayalam",
}

_MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "hi": ["जन॰", "फ़र॰", "मार्च", "अप्रैल", "मई", "जून", "जुल॰", "अग॰", "सित॰", "अक्तू॰", "नव॰", "दिस॰"],
    "pa": ["ਜਨ", "ਫ਼ਰ", "ਮਾਰਚ", "ਅਪ੍ਰੈ", "ਮਈ", "ਜੂਨ", "ਜੁਲਾ", "ਅਗ", "ਸਤੰ", "ਅਕਤੂ", "ਨਵੰ", "ਦਸੰ"],
    "mr": ["जाने", "फेब्रु", "मार्च", "एप्रि", "मे", "जून", "जुलै", "ऑग", "सप्टें", "ऑक्टो", "नोव्हें", "डिसें"],
    "gu": ["જાન્યુ", "ફેબ્રુ", "માર્ચ", "એપ્રિલ", "મે", "જૂન", "જુલાઈ", "ઑગસ્ટ", "સપ્ટે", "ઑક્ટો", "નવે", "ડિસે"],
    "ur": ["جنوری", "فروری", "مارچ", "اپریل", "مئی", "جون", "جولائی", "اگست", "ستمبر", "اکتوبر", "نومبر", "دسمبر"],
    "ta": ["ஜன.", "பிப்.", "மார்.", "ஏப்.", "மே", "ஜூன்", "ஜூலை", "ஆக.", "செப்.", "அக்.", "நவ.", "டிச."],
    "ml": ["ജനു", "ഫെബ്രു", "മാർ", "ഏപ്രി", "മേയ്", "ജൂൺ", "ജൂലൈ", "ഓഗ", "സെപ്റ്റം", "ഒക്ടോ", "നവം", "ഡിസം"],
}


def normalise_locale(value: str | None) -> str:
    if not value:
        return DEFAULT_LOCALE
    for part in value.replace("_", "-").split(","):
        code = part.split(";")[0].strip().split("-")[0].lower()
        if code in LOCALES:
            return code
    return DEFAULT_LOCALE


def format_inr(amount: Decimal | int | float | None) -> str:
    """₹1,00,000 style Indian grouping, Western digits in every locale (Part 1 §8.1)."""
    if amount is None:
        return ""
    value = Decimal(str(amount)).quantize(Decimal("0.01"))
    negative = value < 0
    value = abs(value)
    whole, frac = divmod(value, 1)
    digits = str(int(whole))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    out = f"₹{digits}"
    if frac:
        out += f".{int(frac * 100):02d}"
    return ("-" if negative else "") + out


def format_date(value: date | datetime | None, locale: str = DEFAULT_LOCALE) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.astimezone(IST).date()
    months = _MONTHS.get(locale, _MONTHS["en"])
    return f"{value.day} {months[value.month - 1]} {value.year}"


# ---------------------------------------------------------------------------------------
# Catalogue. `{name}` placeholders are filled with str.format_map.
# Tone rules (Part 1 §8.3): warm, never blame, never "fake" for artisans.
# Non-English/Hindi strings are machine-assisted and flagged for native review.
# ---------------------------------------------------------------------------------------

CATALOGUE: dict[str, dict[str, str]] = {
    "tip.add_video": {
        "en": "Add a short video of you making it",
        "hi": "इसे बनाते हुए अपना एक छोटा वीडियो जोड़ें",
        "pa": "ਇਸ ਨੂੰ ਬਣਾਉਂਦੇ ਹੋਏ ਆਪਣੀ ਇੱਕ ਛੋਟੀ ਵੀਡੀਓ ਜੋੜੋ",
        "mr": "हे बनवतानाचा तुमचा एक छोटा व्हिडिओ जोडा",
        "gu": "આ બનાવતા હોય એવો તમારો એક નાનો વીડિયો ઉમેરો",
        "ur": "اسے بناتے ہوئے اپنی ایک مختصر ویڈیو شامل کریں",
        "ta": "இதை நீங்கள் செய்யும் ஒரு சிறிய வீடியோவைச் சேர்க்கவும்",
        "ml": "ഇത് നിർമ്മിക്കുന്നതിന്റെ ഒരു ചെറിയ വീഡിയോ ചേർക്കൂ",
    },
    "tip.retake_photos": {
        "en": "Retake photos in daylight on a plain background",
        "hi": "दिन की रोशनी में, सादे पृष्ठभूमि पर फिर से फ़ोटो लें",
        "pa": "ਦਿਨ ਦੀ ਰੌਸ਼ਨੀ ਵਿੱਚ ਸਾਦੇ ਪਿਛੋਕੜ 'ਤੇ ਦੁਬਾਰਾ ਫ਼ੋਟੋ ਲਓ",
        "mr": "दिवसाच्या उजेडात साध्या पार्श्वभूमीवर पुन्हा फोटो काढा",
        "gu": "દિવસના પ્રકાશમાં સાદી પૃષ્ઠભૂમિ પર ફરીથી ફોટા લો",
        "ur": "دن کی روشنی میں سادہ پس منظر پر دوبارہ تصاویر لیں",
        "ta": "பகல் வெளிச்சத்தில் வெற்றுப் பின்னணியில் மீண்டும் புகைப்படம் எடுக்கவும்",
        "ml": "പകൽ വെളിച്ചത്തിൽ ലളിതമായ പശ്ചാത്തലത്തിൽ വീണ്ടും ഫോട്ടോ എടുക്കൂ",
    },
    "tip.photos_look_machine_made": {
        "en": "Show close-ups of the handwork (weave, brush marks, tool marks) so the handmade details are clear",
        "hi": "हाथ के काम की नज़दीकी फ़ोटो दिखाएँ (बुनाई, ब्रश या औज़ार के निशान), ताकि हस्तनिर्मित बारीकियाँ साफ़ दिखें",
        "pa": "ਹੱਥ ਦੇ ਕੰਮ ਦੀਆਂ ਨੇੜਿਓਂ ਫ਼ੋਟੋਆਂ ਦਿਖਾਓ (ਬੁਣਾਈ, ਬੁਰਸ਼ ਜਾਂ ਔਜ਼ਾਰ ਦੇ ਨਿਸ਼ਾਨ)",
        "mr": "हातकामाचे जवळून फोटो दाखवा (विणकाम, ब्रश किंवा हत्यारांच्या खुणा)",
        "gu": "હાથકામના નજીકથી ફોટા બતાવો (વણાટ, બ્રશ કે સાધનના નિશાન)",
        "ur": "ہاتھ کے کام کی قریبی تصاویر دکھائیں (بُنائی، برش یا اوزار کے نشان)",
        "ta": "கைவேலையின் நெருக்கமான புகைப்படங்களைக் காட்டுங்கள் (நெசவு, தூரிகை அல்லது கருவி அடையாளங்கள்)",
        "ml": "കൈപ്പണിയുടെ അടുത്തുനിന്നുള്ള ഫോട്ടോകൾ കാണിക്കൂ (നെയ്ത്ത്, ബ്രഷ് അല്ലെങ്കിൽ ഉപകരണ അടയാളങ്ങൾ)",
    },
    "tip.verify_aadhaar": {
        "en": "Verify your Aadhaar to strengthen your record",
        "hi": "अपना रिकॉर्ड मज़बूत करने के लिए आधार सत्यापित करें",
        "pa": "ਆਪਣਾ ਰਿਕਾਰਡ ਮਜ਼ਬੂਤ ਕਰਨ ਲਈ ਆਧਾਰ ਤਸਦੀਕ ਕਰੋ",
        "mr": "तुमचा रेकॉर्ड मजबूत करण्यासाठी आधार पडताळा",
        "gu": "તમારો રેકોર્ડ મજબૂત કરવા આધાર ચકાસો",
        "ur": "اپنا ریکارڈ مضبوط کرنے کے لیے آدھار کی تصدیق کریں",
        "ta": "உங்கள் பதிவை வலுப்படுத்த ஆதாரைச் சரிபார்க்கவும்",
        "ml": "നിങ്ങളുടെ റെക്കോർഡ് ശക്തമാക്കാൻ ആധാർ സ്ഥിരീകരിക്കൂ",
    },
    "tip.video_show_process": {
        "en": "Show your hands working on this piece, with the loom, wheel or tools in view",
        "hi": "वीडियो में इस चीज़ पर काम करते अपने हाथ और करघा, चाक या औज़ार दिखाएँ",
        "pa": "ਵੀਡੀਓ ਵਿੱਚ ਇਸ 'ਤੇ ਕੰਮ ਕਰਦੇ ਆਪਣੇ ਹੱਥ ਅਤੇ ਖੱਡੀ, ਚੱਕ ਜਾਂ ਔਜ਼ਾਰ ਦਿਖਾਓ",
        "mr": "व्हिडिओमध्ये यावर काम करणारे तुमचे हात आणि माग, चाक किंवा हत्यारे दाखवा",
        "gu": "વીડિયોમાં આના પર કામ કરતા તમારા હાથ અને સાળ, ચાકડો કે સાધનો બતાવો",
        "ur": "ویڈیو میں اس پر کام کرتے اپنے ہاتھ اور کرگھا، چاک یا اوزار دکھائیں",
        "ta": "இந்தப் பொருளில் வேலை செய்யும் உங்கள் கைகளையும் தறி, சக்கரம் அல்லது கருவிகளையும் காட்டுங்கள்",
        "ml": "ഇതിൽ പണിയെടുക്കുന്ന നിങ്ങളുടെ കൈകളും തറി, ചക്രം അല്ലെങ്കിൽ ഉപകരണങ്ങളും കാണിക്കൂ",
    },
    "tip.video_show_product": {
        "en": "End the video by showing the finished piece clearly",
        "hi": "वीडियो के अंत में तैयार चीज़ को साफ़ दिखाएँ",
        "pa": "ਵੀਡੀਓ ਦੇ ਅੰਤ ਵਿੱਚ ਤਿਆਰ ਚੀਜ਼ ਸਾਫ਼ ਦਿਖਾਓ",
        "mr": "व्हिडिओच्या शेवटी तयार वस्तू स्पष्ट दाखवा",
        "gu": "વીડિયોના અંતે તૈયાર વસ્તુ સ્પષ્ટ બતાવો",
        "ur": "ویڈیو کے آخر میں تیار چیز صاف دکھائیں",
        "ta": "வீடியோவின் முடிவில் முடிந்த பொருளைத் தெளிவாகக் காட்டுங்கள்",
        "ml": "വീഡിയോയുടെ അവസാനം പൂർത്തിയായ വസ്തു വ്യക്തമായി കാണിക്കൂ",
    },
    "tip.under_review": {
        "en": "We couldn't verify this product. Our team will look into it.",
        "hi": "हम इस उत्पाद को सत्यापित नहीं कर पाए। हमारी टीम इसे देखेगी।",
        "pa": "ਅਸੀਂ ਇਸ ਉਤਪਾਦ ਦੀ ਤਸਦੀਕ ਨਹੀਂ ਕਰ ਸਕੇ। ਸਾਡੀ ਟੀਮ ਇਸ ਨੂੰ ਵੇਖੇਗੀ।",
        "mr": "आम्ही हे उत्पादन पडताळू शकलो नाही. आमची टीम ते पाहील.",
        "gu": "અમે આ ઉત્પાદન ચકાસી શક્યા નથી. અમારી ટીમ તેને જોશે.",
        "ur": "ہم اس پروڈکٹ کی تصدیق نہیں کر سکے۔ ہماری ٹیم اسے دیکھے گی۔",
        "ta": "இந்தப் பொருளை எங்களால் சரிபார்க்க முடியவில்லை. எங்கள் குழு இதைப் பார்க்கும்.",
        "ml": "ഈ ഉൽപ്പന്നം ഞങ്ങൾക്ക് സ്ഥിരീകരിക്കാനായില്ല. ഞങ്ങളുടെ ടീം ഇത് പരിശോധിക്കും.",
    },
    "price.below": {
        "en": "Shops sell similar {basis_label} for {low}–{high}. Your price is {price}.",
        "hi": "दुकानें ऐसी ही {basis_label} {low}–{high} में बेचती हैं। आपकी कीमत {price} है।",
        "pa": "ਦੁਕਾਨਾਂ ਅਜਿਹੀਆਂ {basis_label} {low}–{high} ਵਿੱਚ ਵੇਚਦੀਆਂ ਹਨ। ਤੁਹਾਡੀ ਕੀਮਤ {price} ਹੈ।",
        "mr": "दुकाने अशाच {basis_label} {low}–{high} ला विकतात. तुमची किंमत {price} आहे.",
        "gu": "દુકાનો આવી જ {basis_label} {low}–{high} માં વેચે છે. તમારી કિંમત {price} છે.",
        "ur": "دکانیں ایسی ہی {basis_label} {low}–{high} میں بیچتی ہیں۔ آپ کی قیمت {price} ہے۔",
        "ta": "கடைகள் இதுபோன்ற {basis_label} {low}–{high} க்கு விற்கின்றன. உங்கள் விலை {price}.",
        "ml": "കടകൾ സമാനമായ {basis_label} {low}–{high} ന് വിൽക്കുന്നു. നിങ്ങളുടെ വില {price} ആണ്.",
    },
    "price.in_range": {
        "en": "Your price {price} is in line with similar {basis_label} ({low}–{high}).",
        "hi": "आपकी कीमत {price} ऐसी ही {basis_label} ({low}–{high}) के बराबर है।",
        "pa": "ਤੁਹਾਡੀ ਕੀਮਤ {price} ਅਜਿਹੀਆਂ {basis_label} ({low}–{high}) ਦੇ ਬਰਾਬਰ ਹੈ।",
        "mr": "तुमची किंमत {price} अशाच {basis_label} ({low}–{high}) प्रमाणे आहे.",
        "gu": "તમારી કિંમત {price} આવી જ {basis_label} ({low}–{high}) જેટલી છે.",
        "ur": "آپ کی قیمت {price} ایسی ہی {basis_label} ({low}–{high}) کے برابر ہے۔",
        "ta": "உங்கள் விலை {price} இதுபோன்ற {basis_label} ({low}–{high}) க்கு ஏற்ப உள்ளது.",
        "ml": "നിങ്ങളുടെ വില {price} സമാനമായ {basis_label} ({low}–{high}) ന് അനുസൃതമാണ്.",
    },
    "price.above": {
        "en": "Shops sell similar {basis_label} for {low}–{high}. Your price {price} is above most of them.",
        "hi": "दुकानें ऐसी ही {basis_label} {low}–{high} में बेचती हैं। आपकी कीमत {price} ज़्यादातर से ऊपर है।",
        "pa": "ਦੁਕਾਨਾਂ ਅਜਿਹੀਆਂ {basis_label} {low}–{high} ਵਿੱਚ ਵੇਚਦੀਆਂ ਹਨ। ਤੁਹਾਡੀ ਕੀਮਤ {price} ਜ਼ਿਆਦਾਤਰ ਤੋਂ ਉੱਪਰ ਹੈ।",
        "mr": "दुकाने अशाच {basis_label} {low}–{high} ला विकतात. तुमची किंमत {price} बहुतेकांपेक्षा जास्त आहे.",
        "gu": "દુકાનો આવી જ {basis_label} {low}–{high} માં વેચે છે. તમારી કિંમત {price} મોટાભાગની કરતાં વધુ છે.",
        "ur": "دکانیں ایسی ہی {basis_label} {low}–{high} میں بیچتی ہیں۔ آپ کی قیمت {price} زیادہ تر سے اوپر ہے۔",
        "ta": "கடைகள் இதுபோன்ற {basis_label} {low}–{high} க்கு விற்கின்றன. உங்கள் விலை {price} பெரும்பாலானவற்றை விட அதிகம்.",
        "ml": "കടകൾ സമാനമായ {basis_label} {low}–{high} ന് വിൽക്കുന്നു. നിങ്ങളുടെ വില {price} മിക്കവയെക്കാളും കൂടുതലാണ്.",
    },
    "price.unverified_compare": {
        "en": "Unverified pieces like this sell for {rlow}–{rhigh}. Verified ones sell for {hlow}–{hhigh}. Add a making video to get verified.",
        "hi": "ऐसी असत्यापित चीज़ें {rlow}–{rhigh} में बिकती हैं। सत्यापित चीज़ें {hlow}–{hhigh} में बिकती हैं। सत्यापन के लिए बनाने का वीडियो जोड़ें।",
        "pa": "ਅਜਿਹੀਆਂ ਗ਼ੈਰ-ਤਸਦੀਕਸ਼ੁਦਾ ਚੀਜ਼ਾਂ {rlow}–{rhigh} ਵਿੱਚ ਵਿਕਦੀਆਂ ਹਨ। ਤਸਦੀਕਸ਼ੁਦਾ {hlow}–{hhigh} ਵਿੱਚ। ਤਸਦੀਕ ਲਈ ਬਣਾਉਣ ਦੀ ਵੀਡੀਓ ਜੋੜੋ।",
        "mr": "अशा अपडताळलेल्या वस्तू {rlow}–{rhigh} ला विकल्या जातात. पडताळलेल्या {hlow}–{hhigh} ला. पडताळणीसाठी बनवतानाचा व्हिडिओ जोडा.",
        "gu": "આવી બિન-ચકાસાયેલ વસ્તુઓ {rlow}–{rhigh} માં વેચાય છે. ચકાસાયેલ {hlow}–{hhigh} માં. ચકાસણી માટે બનાવવાનો વીડિયો ઉમેરો.",
        "ur": "ایسی غیر تصدیق شدہ چیزیں {rlow}–{rhigh} میں بکتی ہیں۔ تصدیق شدہ {hlow}–{hhigh} میں۔ تصدیق کے لیے بنانے کی ویڈیو شامل کریں۔",
        "ta": "சரிபார்க்கப்படாத இதுபோன்றவை {rlow}–{rhigh} க்கு விற்கின்றன. சரிபார்க்கப்பட்டவை {hlow}–{hhigh} க்கு. சரிபார்ப்புக்கு செய்முறை வீடியோவைச் சேர்க்கவும்.",
        "ml": "സ്ഥിരീകരിക്കാത്ത ഇത്തരം വസ്തുക്കൾ {rlow}–{rhigh} ന് വിൽക്കുന്നു. സ്ഥിരീകരിച്ചവ {hlow}–{hhigh} ന്. സ്ഥിരീകരണത്തിന് നിർമ്മാണ വീഡിയോ ചേർക്കൂ.",
    },
    "price.insufficient": {
        "en": "Not enough market data yet",
        "hi": "अभी पर्याप्त बाज़ार जानकारी नहीं है",
        "pa": "ਹਾਲੇ ਲੋੜੀਂਦੀ ਬਾਜ਼ਾਰ ਜਾਣਕਾਰੀ ਨਹੀਂ ਹੈ",
        "mr": "अजून पुरेशी बाजार माहिती नाही",
        "gu": "હજુ પૂરતી બજાર માહિતી નથી",
        "ur": "ابھی کافی مارکیٹ معلومات نہیں ہیں",
        "ta": "இன்னும் போதுமான சந்தைத் தரவு இல்லை",
        "ml": "മതിയായ വിപണി വിവരങ്ങൾ ഇതുവരെ ഇല്ല",
    },
    "price.basis.handmade": {
        "en": "handmade pieces", "hi": "हस्तनिर्मित चीज़ें", "pa": "ਹੱਥ ਨਾਲ ਬਣੀਆਂ ਚੀਜ਼ਾਂ", "mr": "हस्तनिर्मित वस्तू",
        "gu": "હાથબનાવટની વસ્તુઓ", "ur": "ہاتھ سے بنی چیزیں", "ta": "கைவினைப் பொருட்கள்", "ml": "കൈത്തറി/കൈപ്പണി വസ്തുക്കൾ",
    },
    "price.basis.replica": {
        "en": "unverified pieces", "hi": "असत्यापित चीज़ें", "pa": "ਗ਼ੈਰ-ਤਸਦੀਕਸ਼ੁਦਾ ਚੀਜ਼ਾਂ", "mr": "अपडताळलेल्या वस्तू",
        "gu": "બિન-ચકાસાયેલ વસ્તુઓ", "ur": "غیر تصدیق شدہ چیزیں", "ta": "சரிபார்க்கப்படாத பொருட்கள்", "ml": "സ്ഥിരീകരിക്കാത്ത വസ്തുക്കൾ",
    },
    "notif.otp": {
        "en": "{code} is your Karu code. It expires in 5 minutes. Don't share it.",
        "hi": "{code} आपका कारू कोड है। यह 5 मिनट में समाप्त होगा। इसे किसी से साझा न करें।",
        "pa": "{code} ਤੁਹਾਡਾ ਕਾਰੂ ਕੋਡ ਹੈ। ਇਹ 5 ਮਿੰਟ ਵਿੱਚ ਖ਼ਤਮ ਹੋਵੇਗਾ। ਕਿਸੇ ਨਾਲ ਸਾਂਝਾ ਨਾ ਕਰੋ।",
        "mr": "{code} हा तुमचा कारू कोड आहे. तो 5 मिनिटांत संपेल. कोणालाही सांगू नका.",
        "gu": "{code} તમારો કારુ કોડ છે. તે 5 મિનિટમાં સમાપ્ત થશે. કોઈને જણાવશો નહીં.",
        "ur": "{code} آپ کا کارو کوڈ ہے۔ یہ 5 منٹ میں ختم ہو جائے گا۔ کسی سے شیئر نہ کریں۔",
        "ta": "{code} உங்கள் காரு குறியீடு. இது 5 நிமிடங்களில் காலாவதியாகும். யாருடனும் பகிர வேண்டாம்.",
        "ml": "{code} ആണ് നിങ്ങളുടെ കാരു കോഡ്. ഇത് 5 മിനിറ്റിൽ കാലഹരണപ്പെടും. ആരുമായും പങ്കിടരുത്.",
    },
    "notif.listing_published": {
        "en": "Your {title} is live on Karu! {count} Karu IDs created.",
        "hi": "आपका {title} कारू पर लाइव है! {count} कारू आईडी बनाए गए।",
        "pa": "ਤੁਹਾਡਾ {title} ਕਾਰੂ 'ਤੇ ਲਾਈਵ ਹੈ! {count} ਕਾਰੂ ਆਈਡੀ ਬਣਾਏ ਗਏ।",
        "mr": "तुमचे {title} कारूवर लाइव्ह आहे! {count} कारू आयडी तयार झाले.",
        "gu": "તમારું {title} કારુ પર લાઇવ છે! {count} કારુ આઈડી બન્યા.",
        "ur": "آپ کا {title} کارو پر لائیو ہے! {count} کارو آئی ڈی بنائے گئے۔",
        "ta": "உங்கள் {title} காருவில் வெளியானது! {count} காரு ஐடிகள் உருவாக்கப்பட்டன.",
        "ml": "നിങ്ങളുടെ {title} കാരുവിൽ ലൈവാണ്! {count} കാരു ഐഡികൾ സൃഷ്ടിച്ചു.",
    },
    "notif.verification_verified": {
        "en": "Good news! Your {title} is now Karu Verified. Share it with your buyers.",
        "hi": "खुशखबरी! आपका {title} अब कारू सत्यापित है। इसे अपने ग्राहकों के साथ साझा करें।",
        "pa": "ਖ਼ੁਸ਼ਖ਼ਬਰੀ! ਤੁਹਾਡਾ {title} ਹੁਣ ਕਾਰੂ ਤਸਦੀਕਸ਼ੁਦਾ ਹੈ। ਇਸ ਨੂੰ ਆਪਣੇ ਖ਼ਰੀਦਦਾਰਾਂ ਨਾਲ ਸਾਂਝਾ ਕਰੋ।",
        "mr": "आनंदाची बातमी! तुमचे {title} आता कारू पडताळलेले आहे. ग्राहकांसोबत शेअर करा.",
        "gu": "ખુશખબર! તમારું {title} હવે કારુ ચકાસાયેલ છે. તમારા ગ્રાહકો સાથે શેર કરો.",
        "ur": "خوشخبری! آپ کا {title} اب کارو سے تصدیق شدہ ہے۔ اسے اپنے خریداروں سے شیئر کریں۔",
        "ta": "நல்ல செய்தி! உங்கள் {title} இப்போது காரு சரிபார்க்கப்பட்டது. வாங்குபவர்களுடன் பகிருங்கள்.",
        "ml": "സന്തോഷവാർത്ത! നിങ്ങളുടെ {title} ഇപ്പോൾ കാരു സ്ഥിരീകരിച്ചതാണ്. വാങ്ങുന്നവരുമായി പങ്കിടൂ.",
    },
    "notif.verification_not_verified": {
        "en": "Your {title} is not verified yet. Open Karu to see what to add, then try again.",
        "hi": "आपका {title} अभी सत्यापित नहीं हुआ है। क्या जोड़ना है यह देखने के लिए कारू खोलें, फिर दोबारा कोशिश करें।",
        "pa": "ਤੁਹਾਡਾ {title} ਹਾਲੇ ਤਸਦੀਕ ਨਹੀਂ ਹੋਇਆ। ਕੀ ਜੋੜਨਾ ਹੈ ਵੇਖਣ ਲਈ ਕਾਰੂ ਖੋਲ੍ਹੋ, ਫਿਰ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
        "mr": "तुमचे {title} अजून पडताळले नाही. काय जोडायचे ते पाहण्यासाठी कारू उघडा आणि पुन्हा प्रयत्न करा.",
        "gu": "તમારું {title} હજુ ચકાસાયું નથી. શું ઉમેરવું તે જોવા કારુ ખોલો, પછી ફરી પ્રયાસ કરો.",
        "ur": "آپ کا {title} ابھی تصدیق شدہ نہیں ہے۔ کیا شامل کرنا ہے دیکھنے کے لیے کارو کھولیں، پھر دوبارہ کوشش کریں۔",
        "ta": "உங்கள் {title} இன்னும் சரிபார்க்கப்படவில்லை. என்ன சேர்க்க வேண்டும் என்று பார்க்க காருவைத் திறந்து மீண்டும் முயலுங்கள்.",
        "ml": "നിങ്ങളുടെ {title} ഇതുവരെ സ്ഥിരീകരിച്ചിട്ടില്ല. എന്ത് ചേർക്കണമെന്ന് കാണാൻ കാരു തുറന്ന് വീണ്ടും ശ്രമിക്കൂ.",
    },
    "notif.new_order": {
        "en": "New order! {buyer} from {city} bought your {title}. Please pack it with Karu ID {karu_id}.",
        "hi": "नया ऑर्डर! {city} के {buyer} ने आपका {title} खरीदा। कृपया इसे कारू आईडी {karu_id} के साथ पैक करें।",
        "pa": "ਨਵਾਂ ਆਰਡਰ! {city} ਦੇ {buyer} ਨੇ ਤੁਹਾਡਾ {title} ਖ਼ਰੀਦਿਆ। ਕਿਰਪਾ ਕਰਕੇ ਕਾਰੂ ਆਈਡੀ {karu_id} ਨਾਲ ਪੈਕ ਕਰੋ।",
        "mr": "नवीन ऑर्डर! {city} मधील {buyer} यांनी तुमचे {title} घेतले. कृपया कारू आयडी {karu_id} सह पॅक करा.",
        "gu": "નવો ઓર્ડર! {city} ના {buyer} એ તમારું {title} ખરીદ્યું. કૃપા કરી કારુ આઈડી {karu_id} સાથે પેક કરો.",
        "ur": "نیا آرڈر! {city} کے {buyer} نے آپ کا {title} خریدا۔ براہ کرم کارو آئی ڈی {karu_id} کے ساتھ پیک کریں۔",
        "ta": "புதிய ஆர்டர்! {city} இலிருந்து {buyer} உங்கள் {title} ஐ வாங்கினார். காரு ஐடி {karu_id} உடன் பேக் செய்யவும்.",
        "ml": "പുതിയ ഓർഡർ! {city} യിൽ നിന്ന് {buyer} നിങ്ങളുടെ {title} വാങ്ങി. കാരു ഐഡി {karu_id} സഹിതം പായ്ക്ക് ചെയ്യൂ.",
    },
    "notif.ship_reminder": {
        "en": "Reminder: please ship order {order_number} ({title}).",
        "hi": "याद दिलाना: कृपया ऑर्डर {order_number} ({title}) भेजें।",
        "pa": "ਯਾਦ ਦਿਵਾਉਣਾ: ਕਿਰਪਾ ਕਰਕੇ ਆਰਡਰ {order_number} ({title}) ਭੇਜੋ।",
        "mr": "आठवण: कृपया ऑर्डर {order_number} ({title}) पाठवा.",
        "gu": "યાદ અપાવવું: કૃપા કરી ઓર્ડર {order_number} ({title}) મોકલો.",
        "ur": "یاد دہانی: براہ کرم آرڈر {order_number} ({title}) بھیجیں۔",
        "ta": "நினைவூட்டல்: ஆர்டர் {order_number} ({title}) ஐ அனுப்பவும்.",
        "ml": "ഓർമ്മപ്പെടുത്തൽ: ഓർഡർ {order_number} ({title}) അയക്കൂ.",
    },
    "notif.order_confirmed": {
        "en": "Thank you! Order {order_number} is confirmed. You'll receive Karu ID {karu_ids} with your piece.",
        "hi": "धन्यवाद! ऑर्डर {order_number} की पुष्टि हो गई। आपको अपनी चीज़ के साथ कारू आईडी {karu_ids} मिलेगा।",
    },
    "notif.order_shipped": {
        "en": "Your order {order_number} ({title}) has been shipped. {tracking}",
        "hi": "आपका ऑर्डर {order_number} ({title}) भेज दिया गया है। {tracking}",
    },
    "notif.order_delivered": {
        "en": "Order {order_number} delivered. Scan the Karu tag to meet the maker.",
        "hi": "ऑर्डर {order_number} पहुँच गया। निर्माता से मिलने के लिए कारू टैग स्कैन करें।",
    },
    "notif.order_cancelled": {
        "en": "Order {order_number} was cancelled and a full refund has been started. We're sorry.",
        "hi": "ऑर्डर {order_number} रद्द हुआ और पूरा रिफ़ंड शुरू कर दिया गया है। हमें खेद है।",
    },
    "notif.payout_sent": {
        "en": "{amount} for {title} is on its way to your account.",
        "hi": "{title} के लिए {amount} आपके खाते में भेजे जा रहे हैं।",
        "pa": "{title} ਲਈ {amount} ਤੁਹਾਡੇ ਖਾਤੇ ਵਿੱਚ ਭੇਜੇ ਜਾ ਰਹੇ ਹਨ।",
        "mr": "{title} साठी {amount} तुमच्या खात्यात पाठवले जात आहेत.",
        "gu": "{title} માટે {amount} તમારા ખાતામાં મોકલાઈ રહ્યા છે.",
        "ur": "{title} کے لیے {amount} آپ کے کھاتے میں بھیجے جا رہے ہیں۔",
        "ta": "{title} க்கான {amount} உங்கள் கணக்கிற்கு அனுப்பப்படுகிறது.",
        "ml": "{title} നുള്ള {amount} നിങ്ങളുടെ അക്കൗണ്ടിലേക്ക് അയക്കുന്നു.",
    },
    "notif.payout_failed": {
        "en": "We couldn't send {amount} for {title}. Please check your payout details in Karu.",
        "hi": "हम {title} के लिए {amount} नहीं भेज पाए। कृपया कारू में अपनी भुगतान जानकारी जाँचें।",
        "pa": "ਅਸੀਂ {title} ਲਈ {amount} ਨਹੀਂ ਭੇਜ ਸਕੇ। ਕਿਰਪਾ ਕਰਕੇ ਕਾਰੂ ਵਿੱਚ ਭੁਗਤਾਨ ਵੇਰਵੇ ਜਾਂਚੋ।",
        "mr": "आम्ही {title} साठी {amount} पाठवू शकलो नाही. कृपया कारूमध्ये पेमेंट तपशील तपासा.",
        "gu": "અમે {title} માટે {amount} મોકલી શક્યા નથી. કૃપા કરી કારુમાં ચુકવણી વિગતો તપાસો.",
        "ur": "ہم {title} کے لیے {amount} نہیں بھیج سکے۔ براہ کرم کارو میں ادائیگی کی تفصیلات دیکھیں۔",
        "ta": "{title} க்கான {amount} ஐ அனுப்ப முடியவில்லை. காருவில் உங்கள் பணம் பெறும் விவரங்களைச் சரிபார்க்கவும்.",
        "ml": "{title} നുള്ള {amount} അയക്കാനായില്ല. കാരുവിൽ പേഔട്ട് വിവരങ്ങൾ പരിശോധിക്കൂ.",
    },
    "notif.price_changed": {
        "en": "Market prices for items like your {title} have changed. Open Karu to see the new range.",
        "hi": "आपके {title} जैसी चीज़ों के बाज़ार भाव बदले हैं। नई सीमा देखने के लिए कारू खोलें।",
        "pa": "ਤੁਹਾਡੇ {title} ਵਰਗੀਆਂ ਚੀਜ਼ਾਂ ਦੇ ਬਾਜ਼ਾਰ ਭਾਅ ਬਦਲੇ ਹਨ। ਨਵੀਂ ਰੇਂਜ ਵੇਖਣ ਲਈ ਕਾਰੂ ਖੋਲ੍ਹੋ।",
        "mr": "तुमच्या {title} सारख्या वस्तूंचे बाजारभाव बदलले आहेत. नवीन श्रेणी पाहण्यासाठी कारू उघडा.",
        "gu": "તમારા {title} જેવી વસ્તુઓના બજાર ભાવ બદલાયા છે. નવી શ્રેણી જોવા કારુ ખોલો.",
        "ur": "آپ کے {title} جیسی چیزوں کی مارکیٹ قیمتیں بدلی ہیں۔ نئی حد دیکھنے کے لیے کارو کھولیں۔",
        "ta": "உங்கள் {title} போன்றவற்றின் சந்தை விலைகள் மாறியுள்ளன. புதிய வரம்பைப் பார்க்க காருவைத் திறக்கவும்.",
        "ml": "നിങ്ങളുടെ {title} പോലുള്ളവയുടെ വിപണി വില മാറി. പുതിയ ശ്രേണി കാണാൻ കാരു തുറക്കൂ.",
    },
    "notif.make_again_received": {
        "en": "A buyer would like {quantity} more of your {title}. Open Requests in Karu to reply.",
        "hi": "एक ग्राहक आपका {title} {quantity} और चाहते हैं। जवाब देने के लिए कारू में अनुरोध खोलें।",
        "pa": "ਇੱਕ ਖ਼ਰੀਦਦਾਰ ਤੁਹਾਡਾ {title} {quantity} ਹੋਰ ਚਾਹੁੰਦਾ ਹੈ। ਜਵਾਬ ਦੇਣ ਲਈ ਕਾਰੂ ਵਿੱਚ ਬੇਨਤੀਆਂ ਖੋਲ੍ਹੋ।",
        "mr": "एका ग्राहकाला तुमचे {title} आणखी {quantity} हवे आहे. उत्तर देण्यासाठी कारूमध्ये विनंत्या उघडा.",
        "gu": "એક ગ્રાહકને તમારું {title} વધુ {quantity} જોઈએ છે. જવાબ આપવા કારુમાં વિનંતીઓ ખોલો.",
        "ur": "ایک خریدار آپ کا {title} مزید {quantity} چاہتا ہے۔ جواب دینے کے لیے کارو میں درخواستیں کھولیں۔",
        "ta": "ஒரு வாங்குபவர் உங்கள் {title} இன்னும் {quantity} வேண்டும் என்கிறார். பதிலளிக்க காருவில் கோரிக்கைகளைத் திறக்கவும்.",
        "ml": "ഒരു വാങ്ങുന്നയാൾക്ക് നിങ്ങളുടെ {title} {quantity} എണ്ണം കൂടി വേണം. മറുപടി നൽകാൻ കാരുവിൽ അഭ്യർത്ഥനകൾ തുറക്കൂ.",
    },
    "notif.make_again_answered": {
        "en": "{maker} replied to your request for {title}: {reply}",
        "hi": "{maker} ने {title} के आपके अनुरोध का जवाब दिया: {reply}",
    },
    "notif.bulk_opportunity": {
        "en": "New bulk order opportunity: {quantity} × {product} by {deadline}. Open Requests in Karu to join.",
        "hi": "नया थोक ऑर्डर अवसर: {deadline} तक {quantity} × {product}। जुड़ने के लिए कारू में अनुरोध खोलें।",
        "pa": "ਨਵਾਂ ਥੋਕ ਆਰਡਰ ਮੌਕਾ: {deadline} ਤੱਕ {quantity} × {product}। ਸ਼ਾਮਲ ਹੋਣ ਲਈ ਕਾਰੂ ਵਿੱਚ ਬੇਨਤੀਆਂ ਖੋਲ੍ਹੋ।",
        "mr": "नवीन घाऊक ऑर्डर संधी: {deadline} पर्यंत {quantity} × {product}. सहभागी होण्यासाठी कारूमध्ये विनंत्या उघडा.",
        "gu": "નવી જથ્થાબંધ ઓર્ડર તક: {deadline} સુધી {quantity} × {product}. જોડાવા કારુમાં વિનંતીઓ ખોલો.",
        "ur": "نیا ہول سیل آرڈر موقع: {deadline} تک {quantity} × {product}۔ شامل ہونے کے لیے کارو میں درخواستیں کھولیں۔",
        "ta": "புதிய மொத்த ஆர்டர் வாய்ப்பு: {deadline} க்குள் {quantity} × {product}. சேர காருவில் கோரிக்கைகளைத் திறக்கவும்.",
        "ml": "പുതിയ ബൾക്ക് ഓർഡർ അവസരം: {deadline} നകം {quantity} × {product}. ചേരാൻ കാരുവിൽ അഭ്യർത്ഥനകൾ തുറക്കൂ.",
    },
    "notif.return_requested": {
        "en": "A return was requested for order {order_number} ({title}). Reason: {reason}.",
        "hi": "ऑर्डर {order_number} ({title}) के लिए वापसी का अनुरोध आया है। कारण: {reason}।",
        "pa": "ਆਰਡਰ {order_number} ({title}) ਲਈ ਵਾਪਸੀ ਦੀ ਬੇਨਤੀ ਆਈ ਹੈ। ਕਾਰਨ: {reason}।",
        "mr": "ऑर्डर {order_number} ({title}) साठी परतीची विनंती आली आहे. कारण: {reason}.",
        "gu": "ઓર્ડર {order_number} ({title}) માટે વળતરની વિનંતી આવી છે. કારણ: {reason}.",
        "ur": "آرڈر {order_number} ({title}) کی واپسی کی درخواست آئی ہے۔ وجہ: {reason}۔",
        "ta": "ஆர்டர் {order_number} ({title}) க்கு திருப்பி அனுப்பும் கோரிக்கை வந்துள்ளது. காரணம்: {reason}.",
        "ml": "ഓർഡർ {order_number} ({title}) ന് മടക്കി നൽകൽ അഭ്യർത്ഥന വന്നു. കാരണം: {reason}.",
    },
    "notif.refund_processed": {
        "en": "Your refund of {amount} for order {order_number} has been processed.",
        "hi": "ऑर्डर {order_number} के लिए आपका {amount} का रिफ़ंड हो गया है।",
    },
    "notif.maker_new_product": {
        "en": "{maker} just added a new piece: {title}",
        "hi": "{maker} ने एक नई चीज़ जोड़ी: {title}",
    },
    "notif.passport_verified": {
        "en": "Your Karu Passport is now Verified.",
        "hi": "आपका कारू पासपोर्ट अब सत्यापित है।",
        "pa": "ਤੁਹਾਡਾ ਕਾਰੂ ਪਾਸਪੋਰਟ ਹੁਣ ਤਸਦੀਕਸ਼ੁਦਾ ਹੈ।",
        "mr": "तुमचा कारू पासपोर्ट आता पडताळलेला आहे.",
        "gu": "તમારો કારુ પાસપોર્ટ હવે ચકાસાયેલ છે.",
        "ur": "آپ کا کارو پاسپورٹ اب تصدیق شدہ ہے۔",
        "ta": "உங்கள் காரு பாஸ்போர்ட் இப்போது சரிபார்க்கப்பட்டது.",
        "ml": "നിങ്ങളുടെ കാരു പാസ്പോർട്ട് ഇപ്പോൾ സ്ഥിരീകരിച്ചതാണ്.",
    },
    "share.caption": {
        "en": "{title} — handmade by {maker} in {place}. Scan the Karu QR or open {url} to see the proof.",
        "hi": "{title} — {place} में {maker} द्वारा हाथ से बना। प्रमाण देखने के लिए कारू QR स्कैन करें या {url} खोलें।",
        "pa": "{title} — {place} ਵਿੱਚ {maker} ਵੱਲੋਂ ਹੱਥ ਨਾਲ ਬਣਿਆ। ਸਬੂਤ ਵੇਖਣ ਲਈ ਕਾਰੂ QR ਸਕੈਨ ਕਰੋ ਜਾਂ {url} ਖੋਲ੍ਹੋ।",
        "mr": "{title} — {place} येथे {maker} यांनी हाताने बनवलेले. पुरावा पाहण्यासाठी कारू QR स्कॅन करा किंवा {url} उघडा.",
        "gu": "{title} — {place} માં {maker} દ્વારા હાથથી બનાવેલ. પુરાવો જોવા કારુ QR સ્કેન કરો અથવા {url} ખોલો.",
        "ur": "{title} — {place} میں {maker} کا ہاتھ سے بنایا ہوا۔ ثبوت دیکھنے کے لیے کارو QR اسکین کریں یا {url} کھولیں۔",
        "ta": "{title} — {place} இல் {maker} கையால் செய்தது. சான்றைப் பார்க்க காரு QR ஐ ஸ்கேன் செய்யவும் அல்லது {url} ஐத் திறக்கவும்.",
        "ml": "{title} — {place} ൽ {maker} കൈകൊണ്ട് നിർമ്മിച്ചത്. തെളിവ് കാണാൻ കാരു QR സ്കാൻ ചെയ്യൂ അല്ലെങ്കിൽ {url} തുറക്കൂ.",
    },
    "tag.scan": {
        "en": "Scan to meet the maker", "hi": "निर्माता से मिलने के लिए स्कैन करें", "pa": "ਨਿਰਮਾਤਾ ਨੂੰ ਮਿਲਣ ਲਈ ਸਕੈਨ ਕਰੋ",
        "mr": "निर्मात्याला भेटण्यासाठी स्कॅन करा", "gu": "નિર્માતાને મળવા સ્કેન કરો", "ur": "کاریگر سے ملنے کے لیے اسکین کریں",
        "ta": "தயாரிப்பாளரைச் சந்திக்க ஸ்கேன் செய்யவும்", "ml": "നിർമ്മാതാവിനെ കാണാൻ സ്കാൻ ചെയ്യൂ",
    },
    "badge.verified": {
        "en": "Karu Verified", "hi": "कारू सत्यापित", "pa": "ਕਾਰੂ ਤਸਦੀਕਸ਼ੁਦਾ", "mr": "कारू पडताळलेले",
        "gu": "કારુ ચકાસાયેલ", "ur": "کارو تصدیق شدہ", "ta": "காரு சரிபார்க்கப்பட்டது", "ml": "കാരു സ്ഥിരീകരിച്ചത്",
    },
    "badge.not_verified": {
        "en": "Not verified yet", "hi": "अभी सत्यापित नहीं", "pa": "ਹਾਲੇ ਤਸਦੀਕ ਨਹੀਂ", "mr": "अजून पडताळले नाही",
        "gu": "હજુ ચકાસાયેલ નથી", "ur": "ابھی تصدیق شدہ نہیں", "ta": "இன்னும் சரிபார்க்கப்படவில்லை", "ml": "ഇതുവരെ സ്ഥിരീകരിച്ചിട്ടില്ല",
    },
    "return_reason.not_as_described": {"en": "not as described", "hi": "विवरण के अनुसार नहीं"},
    "return_reason.damaged": {"en": "damaged", "hi": "क्षतिग्रस्त"},
    "return_reason.changed_mind": {"en": "changed mind", "hi": "मन बदल गया"},
    "return_reason.other": {"en": "other", "hi": "अन्य"},
}


def t(key: str, locale: str = DEFAULT_LOCALE, **params) -> str:
    entry = CATALOGUE.get(key)
    if not entry:
        return key
    template = entry.get(locale) or entry["en"]

    class _Safe(dict):
        def __missing__(self, k):  # keep unknown placeholders visible instead of crashing
            return "{" + k + "}"

    return template.format_map(_Safe(params))


def pick_lang(values: dict | None, locale: str, fallback_order: tuple[str, ...] = ("en", "hi")) -> tuple[str, str]:
    """Return (text, lang) for a {lang: text} map, falling back sensibly."""
    if not values:
        return "", locale
    if values.get(locale):
        return values[locale], locale
    for lang in fallback_order:
        if values.get(lang):
            return values[lang], lang
    lang, text = next(iter(values.items()))
    return text, lang
