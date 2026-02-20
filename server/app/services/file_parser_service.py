"""File parser service for document processing."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def _extract_docx_text(file_path: str) -> str:
    """Extract DOCX text with better coverage (paragraphs + tables + headers/footers)."""
    from docx import Document
    from docx.document import Document as DocxDocument
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    def iter_block_items(parent):
        if isinstance(parent, DocxDocument):
            parent_elm = parent.element.body
        else:
            parent_elm = parent._element
        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    def normalize(line: str) -> str:
        return " ".join(line.split())

    doc = Document(file_path)
    blocks: list[str] = []

    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = normalize(block.text)
            if text:
                blocks.append(text)
            continue

        if isinstance(block, Table):
            rows: list[str] = []
            for row in block.rows:
                cells = [normalize(cell.text) for cell in row.cells]
                cells = [cell for cell in cells if cell]
                if cells:
                    rows.append(" | ".join(cells))
            if rows:
                blocks.append("\n".join(rows))

    # Include section header/footer texts that are not in body.
    seen_meta: set[str] = set()
    for section in doc.sections:
        for part in (section.header, section.footer):
            for para in part.paragraphs:
                text = normalize(para.text)
                if text and text not in seen_meta:
                    seen_meta.add(text)
                    blocks.append(text)

    return "\n\n".join(blocks)


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
        return _extract_docx_text(file_path)

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
