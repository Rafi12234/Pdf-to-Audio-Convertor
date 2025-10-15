from typing import List
import re

def extract_text_pdfminer(pdf_path: str) -> str:
    """
    Extract text from a PDF using pdfminer.six
    """
    try:
        from pdfminer.high_level import extract_text
        return extract_text(pdf_path) or ""
    except Exception as e:
        print(f"[warn] pdfminer extraction failed: {e}")
        return ""

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")

def smart_chunk(text: str, max_chars: int = 280) -> List[str]:
    """
    Split text into chunks suitable for speech:
    - Prefer sentence boundaries
    - Then limit to ~max_chars per chunk
    """
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Split into sentences
    sentences = re.split(_SENTENCE_SPLIT, text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    buf = []

    def flush_buf():
        if buf:
            chunks.append(" ".join(buf).strip())
            buf.clear()

    current_len = 0
    for s in sentences:
        if current_len + len(s) + 1 <= max_chars:
            buf.append(s)
            current_len += len(s) + 1
        else:
            flush_buf()
            buf.append(s)
            current_len = len(s) + 1
    flush_buf()

    # Safety: split any overly long chunk further at commas/spaces
    refined = []
    for c in chunks:
        if len(c) <= max_chars:
            refined.append(c)
        else:
            refined.extend(_split_long(c, max_chars))
    return refined

def _split_long(text: str, max_chars: int) -> List[str]:
    # Try commas first
    parts = re.split(r",\s*", text)
    out = []
    buf = []
    length = 0
    for p in parts:
        if length + len(p) + 2 <= max_chars:
            buf.append(p)
            length += len(p) + 2
        else:
            if buf:
                out.append(", ".join(buf))
                buf = [p]
                length = len(p) + 2
            else:
                # fallback split by spaces
                out.extend(_split_by_space(p, max_chars))
                length = 0
                buf = []
    if buf:
        out.append(", ".join(buf))
    return out

def _split_by_space(text: str, max_chars: int) -> List[str]:
    words = text.split()
    out, buf = [], []
    length = 0
    for w in words:
        if length + len(w) + 1 <= max_chars:
            buf.append(w)
            length += len(w) + 1
        else:
            out.append(" ".join(buf))
            buf = [w]
            length = len(w) + 1
    if buf:
        out.append(" ".join(buf))
    return out
