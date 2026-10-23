# utils/chunker.py

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """
    Splits text into overlapping chunks.
    chunk_size: characters per chunk (~750 tokens)
    overlap   : characters shared between consecutive chunks
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size

        # Try to break at a sentence boundary (. ! ?)
        if end < text_len:
            for boundary in ['. ', '.\n', '! ', '? ', '\n\n']:
                pos = text.rfind(boundary, start, end)
                if pos != -1:
                    end = pos + len(boundary)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap  # overlap with previous chunk

    return chunks