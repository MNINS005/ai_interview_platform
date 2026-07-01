import pdfplumber


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF resume."""
    pages = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()
