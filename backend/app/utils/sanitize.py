import re


def sanitize_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\x00", "")
    text = text.strip()
    return text
