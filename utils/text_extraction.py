import re
from typing import Tuple, Optional
import pymupdf  # PyMuPDF modern import
import docx

import re
from typing import Tuple, Optional, List
import pymupdf  # PyMuPDF modern import
import docx

def extract_text_from_pdf(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Extracts text from a PDF file using PyMuPDF with spatial layout awareness:
    1. 2-Column Layout Sorting: Computes mid_x = page.rect.width / 2 and sorts
       blocks column-by-column (col0 left, col1 right) sorted by vertical position (y0),
       preventing left-to-right cross-column text scrambling.
    2. Embedded Link Extraction: Scans page.get_links() to capture clickable LinkedIn,
       GitHub, and portfolio URLs that aren't plain text.
    3. Scanned PDF Check: Flags scanned or image-only PDFs if character count < 50.
    """
    text_chunks = []
    extracted_urls = []

    try:
        doc = pymupdf.open(file_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            mid_x = page.rect.width / 2.0

            # 1. Embedded Link Extraction (LinkedIn, GitHub, Portfolios)
            try:
                for link in page.get_links():
                    uri = link.get("uri") or link.get("url")
                    if uri and isinstance(uri, str) and uri.startswith(("http://", "https://", "mailto:")):
                        extracted_urls.append(uri.strip())
            except Exception:
                pass

            # 2. Block extraction with 2-Column layout sorting
            blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
            # Filter to text blocks only (block_type 0)
            valid_blocks = [b for b in blocks if len(b) > 4 and b[4] and b[4].strip() and (len(b) <= 6 or b[6] == 0)]

            if not valid_blocks:
                # Fallback to standard get_text
                raw_page_text = page.get_text("text")
                if raw_page_text and raw_page_text.strip():
                    text_chunks.append(raw_page_text)
                continue

            # Determine if layout is 2-column
            col0 = [b for b in valid_blocks if b[0] < mid_x and b[2] <= mid_x + 35]
            col1 = [b for b in valid_blocks if b[0] >= mid_x - 35]

            # If both columns have significant content (>= 2 blocks each)
            if len(col0) >= 2 and len(col1) >= 2 and (len(col0) + len(col1)) >= (len(valid_blocks) * 0.7):
                # Sort col0 by y0, then col1 by y0
                col0_sorted = sorted(col0, key=lambda b: b[1])
                col1_sorted = sorted(col1, key=lambda b: b[1])
                # Wide header blocks (spanning across center)
                wide_header_blocks = [b for b in valid_blocks if b[0] < mid_x and b[2] > mid_x + 35 and b[1] < min(col0[0][1], col1[0][1])]
                wide_header_blocks.sort(key=lambda b: b[1])
                ordered_blocks = wide_header_blocks + col0_sorted + col1_sorted
            else:
                # Standard single-column flow: sort by vertical y0, then horizontal x0
                ordered_blocks = sorted(valid_blocks, key=lambda b: (b[1], b[0]))

            page_content = "\n".join(b[4].strip() for b in ordered_blocks if b[4].strip())
            if page_content:
                text_chunks.append(page_content)

        doc.close()

        # Append any unique embedded profile links at the end so parsers detect them
        if extracted_urls:
            unique_links = list(dict.fromkeys(extracted_urls))
            text_chunks.append("\nEmbedded Profile Links:\n" + "\n".join(unique_links))

        full_text = "\n\n".join(text_chunks).strip()

        # 3. Scanned PDF Check (< 50 characters)
        if len(full_text) < 50:
            return "", "PDF contains insufficient extractable text (<50 characters). It may be a scanned image or empty document."

        return clean_extracted_text(full_text), None
    except Exception as e:
        return "", f"Error reading PDF: {str(e)}"

def extract_text_from_docx(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Extracts text from a DOCX file using python-docx.
    Reads paragraphs and table cells while stripping out extra whitespace.
    """
    text_chunks = []
    try:
        doc = docx.Document(file_path)
        for p in doc.paragraphs:
            if p.text.strip():
                text_chunks.append(p.text.strip())

        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    text_chunks.append(" | ".join(row_cells))

        full_text = "\n".join(text_chunks).strip()
        if not full_text:
            return "", "DOCX contains no extractable text."

        return clean_extracted_text(full_text), None
    except Exception as e:
        return "", f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Extracts text from plain text formats (.txt).
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()
        if not content:
            return "", "Text file is empty."
        return clean_extracted_text(content), None
    except Exception as e:
        return "", f"Error reading text file: {str(e)}"

def extract_text(file_path: str, file_type: str) -> Tuple[str, Optional[str]]:
    """
    Generic dispatcher for extracting text by file type.
    """
    ext = file_type.lower().strip(".")
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    elif ext in ("docx", "doc"):
        return extract_text_from_docx(file_path)
    elif ext in ("txt", "rtf", "odt"):
        return extract_text_from_txt(file_path)
    else:
        return "", f"Unsupported file type: {ext}"

def clean_extracted_text(text: str) -> str:
    """
    Normalizes spacing, removes redundant empty lines, and standardizes bullet points.
    """
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219]", "*", text)
    text = re.sub(r"[\u2013\u2014]", "-", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
