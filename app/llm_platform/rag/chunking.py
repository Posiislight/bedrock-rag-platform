import re


def chunk_text(text: str, size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into ~size-char chunks with overlap, preferring paragraph/sentence boundaries."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            window = text[start:end]
            cut = max(window.rfind("\n\n"), window.rfind(". "), window.rfind("\n"))
            if cut > size * 0.5:
                end = start + cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks
