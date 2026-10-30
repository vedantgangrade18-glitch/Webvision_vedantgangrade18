"""Lightweight transliteration for search (Part 2 §9.6).

Indic scripts that follow the ISCII layout (Devanagari, Bengali, Gurmukhi, Gujarati,
Oriya, Tamil, Telugu, Kannada, Malayalam) are mapped onto Devanagari by code-point
offset and then romanised in a Hinglish-friendly way. Urdu gets a small consonant map.
`phonetic_key` folds common spelling variants so "banarasi saree", "benarasi sari" and
"बनारसी साड़ी" land close together; fuzzy matching on top handles the rest.

This is intentionally dependency-free. For production-quality output the team can swap
in Aksharamukha / indic-transliteration behind `to_latin` without touching callers.
"""

from __future__ import annotations

import re
import unicodedata

_BRAHMIC_BLOCKS = [0x0900, 0x0980, 0x0A00, 0x0A80, 0x0B00, 0x0B80, 0x0C00, 0x0C80, 0x0D00]

_VOWELS = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri", "ए": "e",
    "ऐ": "ai", "ओ": "o", "औ": "au", "ऍ": "e", "ऑ": "o", "ऎ": "e", "ऒ": "o",
}
_MATRAS = {
    "ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri", "े": "e", "ै": "ai",
    "ो": "o", "ौ": "au", "ॅ": "e", "ॉ": "o", "ॆ": "e", "ॊ": "o",
}
_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j",
    "झ": "jh", "ञ": "n", "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t",
    "थ": "th", "द": "d", "ध": "dh", "न": "n", "ऩ": "n", "प": "p", "फ": "ph", "ब": "b",
    "भ": "bh", "म": "m", "य": "y", "र": "r", "ऱ": "r", "ल": "l", "ळ": "l", "ऴ": "zh",
    "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f", "य़": "y",
}
_NUKTA_FORMS = {"क": "q", "ख": "kh", "ग": "gh", "ज": "z", "ड": "r", "ढ": "rh", "फ": "f", "य": "y"}
_SIGNS = {"ं": "n", "ँ": "n", "ः": "h", "ॐ": "om", "।": ".", "॥": "."}
_VIRAMA = "्"
_NUKTA = "़"

_URDU = {
    "ا": "a", "آ": "aa", "ب": "b", "پ": "p", "ت": "t", "ٹ": "t", "ث": "s", "ج": "j", "چ": "ch",
    "ح": "h", "خ": "kh", "د": "d", "ڈ": "d", "ذ": "z", "ر": "r", "ڑ": "r", "ز": "z", "ژ": "zh",
    "س": "s", "ش": "sh", "ص": "s", "ض": "z", "ط": "t", "ظ": "z", "ع": "a", "غ": "gh", "ف": "f",
    "ق": "q", "ک": "k", "ك": "k", "گ": "g", "ل": "l", "م": "m", "ن": "n", "ں": "n", "و": "o",
    "ہ": "h", "ھ": "h", "ة": "h", "ء": "", "ی": "i", "ي": "i", "ے": "e", "ئ": "i", "ۓ": "e",
}


def _to_devanagari(text: str) -> str:
    out = []
    for ch in text:
        cp = ord(ch)
        for base in _BRAHMIC_BLOCKS[1:]:
            if base <= cp < base + 0x80:
                ch = chr(cp - base + 0x0900)
                break
        out.append(ch)
    return "".join(out)


def _deva_to_latin(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if ch in _CONSONANTS:
            roman = _CONSONANTS[ch]
            if nxt == _NUKTA and ch in _NUKTA_FORMS:
                roman = _NUKTA_FORMS[ch]
                i += 1
                nxt = text[i + 1] if i + 1 < n else ""
            out.append(roman)
            if nxt in _MATRAS:
                out.append(_MATRAS[nxt])
                i += 1
            elif nxt == _VIRAMA:
                i += 1
            else:
                # inherent vowel; dropped at word end (Hindi schwa deletion)
                if nxt in ("ं", "ँ") or (nxt and "ऀ" <= nxt <= "ॿ" and nxt not in _SIGNS):
                    out.append("a")
        elif ch in _VOWELS:
            out.append(_VOWELS[ch])
        elif ch in _MATRAS:
            out.append(_MATRAS[ch])
        elif ch in _SIGNS:
            out.append(_SIGNS[ch])
        elif "०" <= ch <= "९":
            out.append(str(ord(ch) - 0x0966))
        elif ch in (_VIRAMA, _NUKTA):
            pass
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def has_indic(text: str) -> bool:
    return any("ऀ" <= ch <= "෿" or "؀" <= ch <= "ۿ" for ch in text)


def to_latin(text: str) -> str:
    if not text or not has_indic(text):
        return text or ""
    text = _to_devanagari(text)
    text = "".join(_URDU.get(ch, ch) for ch in text)
    return _deva_to_latin(text)


_FOLDS = [
    ("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"), ("ou", "u"),
    ("ph", "f"), ("w", "v"), ("z", "j"), ("q", "k"), ("ck", "k"), ("x", "ks"),
    ("chh", "c"), ("ch", "c"), ("sh", "s"), ("th", "t"), ("dh", "d"), ("bh", "b"),
    ("kh", "k"), ("gh", "g"), ("jh", "j"), ("rh", "r"), ("y", "i"),
]


def _fold_word(word: str) -> str:
    for a, b in _FOLDS:
        word = word.replace(a, b)
    word = re.sub(r"(.)\1+", r"\1", word)
    if len(word) > 4 and word.endswith("a"):
        word = word[:-1]
    if len(word) > 3 and word.endswith("e"):
        word = word[:-1] + "i"
    return word


def phonetic_key(text: str) -> str:
    latin = to_latin(text).lower()
    latin = unicodedata.normalize("NFKD", latin).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", latin)
    return " ".join(_fold_word(w) for w in words)
