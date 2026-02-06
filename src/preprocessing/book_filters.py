def is_junk_page(text: str) -> bool:
    text_lower = text.lower()

    # Strong junk indicators (very late-book sections)
    junk_markers = [
        "bibliography",
        "references",
        "about the author",
        "publisher",
        "copyright",
        "isbn",
    ]

    if any(marker in text_lower for marker in junk_markers):
        return True

    # Extremely short pages are usually headers/footers
    if len(text) < 300:
        return True

    return False
