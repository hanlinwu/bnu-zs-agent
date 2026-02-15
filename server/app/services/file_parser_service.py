"""File parser service for document processing."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_file(file_path: str, file_type: str) -> str:
    """Parse a document file and extract text content.

    Supports: PDF, DOCX, TXT, MD
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_type in ("txt", "md"):
        return path.read_text(encoding="utf-8")

    elif file_type == "pdf":
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return "\n\n".join(text_parts)
        except ImportError:
            logger.warning("pdfplumber not installed, trying PyPDF2")
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    elif file_type == "docx":
        from docx import Document
        doc = Document(file_path)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by character count.

    Uses paragraph boundaries when possible, falls back to character splitting.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If single paragraph exceeds chunk_size, split it
            if len(para) > chunk_size:
                words = para
                while len(words) > chunk_size:
                    chunks.append(words[:chunk_size])
                    words = words[chunk_size - overlap:]
                current_chunk = words
            else:
                # Start new chunk with overlap from previous
                if chunks and overlap > 0:
                    prev_tail = chunks[-1][-overlap:]
                    current_chunk = prev_tail + "\n\n" + para
                else:
                    current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
