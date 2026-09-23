import pymupdf
from pathlib import Path


def extract_text(pdf_path):
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    text_parts = []

    with pymupdf.open(pdf_path) as document:

        for page_number, page in enumerate(document, start=1):

            text = page.get_text("text")

            if text.strip():
                text_parts.append(
                    f"\n--- PAGE {page_number} ---\n"
                )

                text_parts.append(text)

    text = "\n".join(text_parts).strip()

    if not text:
        raise ValueError(
            "No text could be extracted from the PDF."
        )

    return text