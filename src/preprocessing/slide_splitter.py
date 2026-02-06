import re

def split_slide_text(text: str):
    chunks = []

    # Split on bullet points and headings
    parts = re.split(r'[➢•\-–]|(?<=:)', text)

    for part in parts:
        part = part.strip()

        if len(part) < 50:
            continue

        # Split code-heavy sections
        if "{" in part and "}" in part:
            lines = re.split(r';|\n', part)
            for line in lines:
                line = line.strip()
                if len(line) > 40:
                    chunks.append(line)
        else:
            chunks.append(part)

    return chunks
