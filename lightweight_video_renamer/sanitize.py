"""Filename sanitization: Windows/Linux safe, using look-alike characters."""
import re
import unicodedata

LOOKALIKES = {
    ":": "\uff1a",
    "/": "\uff0f",
    "\\": "\uff3c",
    "|": "\uff5c",
    "?": "\uff1f",
    "*": "\uff0a",
    '"': "\uff02",
    "<": "\uff1c",
    ">": "\uff1e",
}
_TABLE = {ord(k): v for k, v in LOOKALIKES.items()}
_RESERVED = {"CON", "PRN", "AUX", "NUL",
             *(f"COM{i}" for i in range(1, 10)),
             *(f"LPT{i}" for i in range(1, 10))}
MAX_BYTES = 255


def sanitize_stem(stem: str, ext: str = "") -> str:
    """Return a safe stem ('' if nothing usable remains). `ext` includes the dot
    and is only used to enforce the 255-byte total length limit."""
    s = unicodedata.normalize("NFC", stem)
    s = re.sub(r"[\x00-\x1f\x7f]", " ", s)
    s = s.translate(_TABLE)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.rstrip(". ")
    if not s:
        return ""
    if s.split(".")[0].upper() in _RESERVED:
        s += "_"
    budget = MAX_BYTES - len(ext.encode("utf-8"))
    while len(s.encode("utf-8")) > budget and s:
        s = s[:-1]
    return s.rstrip(". ")
