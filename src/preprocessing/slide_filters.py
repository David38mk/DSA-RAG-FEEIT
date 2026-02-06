def is_slide_title(text: str) -> bool:
    if len(text) < 40:
        return True

    upper_ratio = sum(c.isupper() for c in text) / max(len(text), 1)

    return upper_ratio > 0.6
