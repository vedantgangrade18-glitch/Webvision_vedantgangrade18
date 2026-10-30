"""Reference data: categories (Part 1 §4.2) with attribute schemas, and crafts/clusters.

Created on startup if missing so a fresh install works; staff can edit later (S06).
Craft heritage texts are short factual summaries written for Karu; GI status reflects the
Geographical Indications registry for these well-known crafts and should be re-checked
by the team before launch.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Category, Craft

# Category.attribute_schema: an ordered list (JSONB doesn't keep dict key order) of field specs.
# `key` is a dotted path into listing.attributes; tier: core = always shown, absence is a real gap;
# badge = feeds verification, shown but never warned about; optional = behind "add more details".
# Labels live in next-intl (sell.review.attr.<last path segment>), not here.
def _f(key: str, type_: str, tier: str) -> dict:
    return {"key": key, "type": type_, "tier": tier}


TEXTILE_ATTRS = {"fields": [
    _f("material", "string", "core"), _f("dimensions.length_m", "number", "core"), _f("technique", "string", "badge"),
    _f("dye", "string", "optional"), _f("colour", "array", "optional"), _f("dimensions.width_m", "number", "optional"),
    _f("time_to_make_days", "integer", "optional"), _f("care", "string", "optional"), _f("weight_g", "integer", "optional"),
]}
OBJECT_ATTRS = {"fields": [
    _f("material", "string", "core"), _f("dimensions.height_cm", "number", "core"), _f("technique", "string", "badge"),
    _f("finish", "string", "optional"), _f("colour", "array", "optional"), _f("dimensions.width_cm", "number", "optional"),
    _f("dimensions.depth_cm", "number", "optional"), _f("time_to_make_days", "integer", "optional"),
    _f("care", "string", "optional"), _f("weight_g", "integer", "optional"),
]}

CATEGORIES = [
    ("sarees", {"en": "Sarees", "hi": "साड़ियाँ", "pa": "ਸਾੜੀਆਂ", "mr": "साड्या", "gu": "સાડીઓ", "ur": "ساڑیاں", "ta": "புடவைகள்", "ml": "സാരികൾ"}, "shirt", TEXTILE_ATTRS),
    ("dupattas-stoles", {"en": "Dupattas & stoles", "hi": "दुपट्टे और स्टोल", "pa": "ਦੁਪੱਟੇ ਅਤੇ ਸਟੋਲ", "mr": "ओढण्या आणि स्टोल", "gu": "દુપટ્ટા અને સ્ટોલ", "ur": "دوپٹے اور اسٹول", "ta": "துப்பட்டாக்கள்", "ml": "ദുപ്പട്ടകൾ"}, "wind", TEXTILE_ATTRS),
    ("kurtas-fabric", {"en": "Kurtas & fabric", "hi": "कुर्ते और कपड़ा", "pa": "ਕੁੜਤੇ ਅਤੇ ਕੱਪੜਾ", "mr": "कुर्ते आणि कापड", "gu": "કુર્તા અને કાપડ", "ur": "کرتے اور کپڑا", "ta": "குர்தாக்கள் & துணி", "ml": "കുർത്തകളും തുണിയും"}, "scissors", TEXTILE_ATTRS),
    ("home-textiles", {"en": "Home textiles", "hi": "घरेलू वस्त्र", "pa": "ਘਰੇਲੂ ਕੱਪੜੇ", "mr": "घरगुती वस्त्रे", "gu": "ઘરના કાપડ", "ur": "گھریلو کپڑے", "ta": "வீட்டுத் துணிகள்", "ml": "ഗൃഹ തുണിത്തരങ്ങൾ"}, "bed-double", TEXTILE_ATTRS),
    ("pottery-terracotta", {"en": "Pottery & terracotta", "hi": "मिट्टी के बर्तन", "pa": "ਮਿੱਟੀ ਦੇ ਭਾਂਡੇ", "mr": "मातीची भांडी", "gu": "માટીના વાસણ", "ur": "مٹی کے برتن", "ta": "மட்பாண்டங்கள்", "ml": "മൺപാത്രങ്ങൾ"}, "amphora", OBJECT_ATTRS),
    ("woodcraft", {"en": "Woodcraft", "hi": "लकड़ी का काम", "pa": "ਲੱਕੜ ਦਾ ਕੰਮ", "mr": "लाकूडकाम", "gu": "લાકડાકામ", "ur": "لکڑی کا کام", "ta": "மரவேலை", "ml": "മരപ്പണി"}, "axe", OBJECT_ATTRS),
    ("metal-brass", {"en": "Metal & brass", "hi": "धातु और पीतल", "pa": "ਧਾਤ ਅਤੇ ਪਿੱਤਲ", "mr": "धातू आणि पितळ", "gu": "ધાતુ અને પિત્તળ", "ur": "دھات اور پیتل", "ta": "உலோகம் & பித்தளை", "ml": "ലോഹവും പിച്ചളയും"}, "bell", OBJECT_ATTRS),
    ("jewellery", {"en": "Jewellery", "hi": "आभूषण", "pa": "ਗਹਿਣੇ", "mr": "दागिने", "gu": "ઘરેણાં", "ur": "زیورات", "ta": "நகைகள்", "ml": "ആഭരണങ്ങൾ"}, "gem", OBJECT_ATTRS),
    ("bamboo-cane", {"en": "Bamboo & cane", "hi": "बांस और बेंत", "pa": "ਬਾਂਸ ਅਤੇ ਬੈਂਤ", "mr": "बांबू आणि वेत", "gu": "વાંસ અને નેતર", "ur": "بانس اور بید", "ta": "மூங்கில் & பிரம்பு", "ml": "മുളയും ചൂരലും"}, "trees", OBJECT_ATTRS),
    ("paintings", {"en": "Paintings", "hi": "चित्रकला", "pa": "ਚਿੱਤਰਕਾਰੀ", "mr": "चित्रकला", "gu": "ચિત્રકળા", "ur": "مصوری", "ta": "ஓவியங்கள்", "ml": "ചിത്രങ്ങൾ"}, "palette", OBJECT_ATTRS),
    ("leather", {"en": "Leather", "hi": "चमड़ा", "pa": "ਚਮੜਾ", "mr": "चामडे", "gu": "ચામડું", "ur": "چمڑا", "ta": "தோல்", "ml": "തുകൽ"}, "footprints", OBJECT_ATTRS),
    ("toys", {"en": "Toys", "hi": "खिलौने", "pa": "ਖਿਡੌਣੇ", "mr": "खेळणी", "gu": "રમકડાં", "ur": "کھلونے", "ta": "பொம்மைகள்", "ml": "കളിപ്പാട്ടങ്ങൾ"}, "toy-brick", OBJECT_ATTRS),
    ("other", {"en": "Other", "hi": "अन्य", "pa": "ਹੋਰ", "mr": "इतर", "gu": "અન્ય", "ur": "دیگر", "ta": "மற்றவை", "ml": "മറ്റുള്ളവ"}, "sparkles", OBJECT_ATTRS),
]

CRAFTS = [
    {
        "slug": "bhagalpuri-silk", "category_slug": "sarees", "gi_tag": True, "regions": ["Bhagalpur, Bihar"],
        "name": {"en": "Bhagalpuri silk", "hi": "भागलपुरी सिल्क"},
        "technique_keywords": ["handloom", "tussar", "silk"],
        "description": {
            "en": "Bhagalpur in Bihar has woven tussar silk on handlooms for generations. The yarn's natural gold "
                  "sheen and slightly uneven texture come from hand reeling and weaving.",
            "hi": "बिहार के भागलपुर में पीढ़ियों से हथकरघे पर टसर रेशम बुना जाता है। हाथ से लपेटे और बुने धागे की "
                  "प्राकृतिक सुनहरी चमक और हल्की असमान बनावट इसकी पहचान है।",
        },
    },
    {
        "slug": "banarasi", "category_slug": "sarees", "gi_tag": True, "regions": ["Varanasi, Uttar Pradesh"],
        "name": {"en": "Banarasi", "hi": "बनारसी"},
        "technique_keywords": ["handloom", "brocade", "zari"],
        "description": {
            "en": "Banarasi brocades are woven in and around Varanasi, often with zari. A genuine handloom Banarasi "
                  "takes days to weeks on the loom; power-loom copies are the craft's biggest threat.",
            "hi": "बनारसी ब्रोकेड वाराणसी और आसपास बुने जाते हैं, अक्सर ज़री के साथ। असली हथकरघा बनारसी को करघे पर "
                  "दिनों से हफ़्तों तक लगते हैं; पावरलूम नकल इस कला के लिए सबसे बड़ा ख़तरा है।",
        },
    },
    {
        "slug": "kutch-embroidery", "category_slug": "dupattas-stoles", "gi_tag": True, "regions": ["Kutch, Gujarat"],
        "name": {"en": "Kutch embroidery", "hi": "कच्छ कढ़ाई"},
        "technique_keywords": ["hand embroidery", "mirror work"],
        "description": {
            "en": "Communities across Kutch embroider with dense stitches and small mirrors, each with its own "
                  "motifs and colours.",
            "hi": "कच्छ के कई समुदाय घने टांकों और छोटे शीशों से कढ़ाई करते हैं, हर समुदाय के अपने रूपांकन और रंग हैं।",
        },
    },
    {
        "slug": "madhubani", "category_slug": "paintings", "gi_tag": True, "regions": ["Mithila, Bihar"],
        "name": {"en": "Madhubani", "hi": "मधुबनी"},
        "technique_keywords": ["hand painted"],
        "description": {
            "en": "Madhubani (Mithila) painting comes from the Mithila region of Bihar: line-filled figures, "
                  "nature and ritual themes, painted by hand with fine brushes and nib pens.",
            "hi": "मधुबनी (मिथिला) चित्रकला बिहार के मिथिला क्षेत्र से है: रेखाओं से भरी आकृतियाँ, प्रकृति और "
                  "अनुष्ठान के विषय, बारीक ब्रश और निब से हाथ से बनाए जाते हैं।",
        },
    },
    {
        "slug": "khurja-pottery", "category_slug": "pottery-terracotta", "gi_tag": True, "regions": ["Khurja, Uttar Pradesh"],
        "name": {"en": "Khurja pottery", "hi": "खुर्जा पॉटरी"},
        "technique_keywords": ["wheel thrown", "glaze"],
        "description": {
            "en": "Khurja potters throw and glaze ceramics in bright, often blue-and-brown glazes.",
            "hi": "खुर्जा के कुम्हार चाक पर बर्तन बनाकर चमकीले, अक्सर नीले-भूरे ग्लेज़ से रंगते हैं।",
        },
    },
    {
        "slug": "dokra", "category_slug": "metal-brass", "gi_tag": True, "regions": ["Bastar, Chhattisgarh", "West Bengal", "Odisha"],
        "name": {"en": "Dokra", "hi": "ढोकरा"},
        "technique_keywords": ["lost wax casting"],
        "description": {
            "en": "Dokra is non-ferrous metal casting using the lost-wax technique, practised for thousands of years.",
            "hi": "ढोकरा मोम-क्षय (लॉस्ट वैक्स) तकनीक से धातु ढलाई है, जो हज़ारों वर्षों से चली आ रही है।",
        },
    },
    {
        "slug": "phulkari", "category_slug": "dupattas-stoles", "gi_tag": True, "regions": ["Punjab"],
        "name": {"en": "Phulkari", "hi": "फुलकारी", "pa": "ਫੁਲਕਾਰੀ"},
        "technique_keywords": ["hand embroidery"],
        "description": {
            "en": "Phulkari — 'flower work' — is Punjab's darning-stitch embroidery in silk floss on hand-spun cloth.",
            "hi": "फुलकारी — 'फूलों का काम' — पंजाब की रेशमी धागे से की जाने वाली कढ़ाई है।",
        },
    },
    {
        "slug": "channapatna-toys", "category_slug": "toys", "gi_tag": True, "regions": ["Channapatna, Karnataka"],
        "name": {"en": "Channapatna toys", "hi": "चन्नपटना खिलौने"},
        "technique_keywords": ["lacquer", "lathe"],
        "description": {
            "en": "Channapatna's lacquered wooden toys are turned on a lathe and coloured with lac.",
            "hi": "चन्नपटना के लाख से रंगे लकड़ी के खिलौने खराद पर बनाए जाते हैं।",
        },
    },
]


async def ensure_reference_data(db: AsyncSession) -> None:
    existing = {c.slug: c for c in (await db.execute(select(Category))).scalars().all()}
    for i, (slug, name, icon, schema) in enumerate(CATEGORIES):
        if slug not in existing:
            db.add(Category(slug=slug, name=name, icon=icon, sort=i, attribute_schema=schema))
        elif existing[slug].attribute_schema != schema:
            existing[slug].attribute_schema = schema  # field specs are code-owned; keep existing DBs in step
    existing_crafts = {c.slug for c in (await db.execute(select(Craft))).scalars().all()}
    for c in CRAFTS:
        if c["slug"] not in existing_crafts:
            db.add(Craft(**c))
    await db.commit()
