import re

def clean_slide_text(text: str) -> str:
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove common slide noise (adjust if needed)
    text = re.sub(r'Page \d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'FEEIT.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Faculty of Electrical.*', '', text, flags=re.IGNORECASE)

    return text.strip()


def clean_book_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
