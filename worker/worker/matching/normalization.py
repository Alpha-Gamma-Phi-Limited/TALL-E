import re


def normalize_identifier(value: str | None) -> str | None:
    if not value:
        return None
    clean = value.upper().strip()
    clean = re.sub(r"[^A-Z0-9/-]", "", clean)
    clean = clean.replace("//", "/")
    return clean or None


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    clean = value.strip().upper()
    clean = re.sub(r"[^A-Z0-9 ]", " ", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean
