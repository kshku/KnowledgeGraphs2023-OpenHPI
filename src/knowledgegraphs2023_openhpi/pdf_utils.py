import json
from pathlib import Path
import pymupdf
import re


TARGETS = (
    re.compile(r"\b1\.\s*Short title"),
    re.compile(r"\b2\.\s*Definitions"),
)


def inspect_pdf(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    with pymupdf.open(path) as document:
        print(f"File: {path.name}")
        print(f"Pages: {len(document)}")
        print(f"Metadata: {document.metadata}")

        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text")

            if not text.strip():
                print(f"\n[Page {page_number}: no extractable text]")
                continue

            print(f"\n{'=' * 20} PAGE {page_number} {'=' * 20}")
            print(text[:2500])


def extract_pdf(pdf_path: Path, output_path: Path) -> None:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with pymupdf.open(pdf_path) as document:
        with output_path.open("w", encoding="utf-8") as output:
            for page_number, page in enumerate(document, start=1):
                record = {
                    "page": page_number,
                    "text": page.get_text("text"),
                }
                output.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"Pages extracted: {len(document)}")
        print(f"Output written to: {output_path}")


def inspect_sections(extracted_file: Path) -> None:
    if not extracted_file.is_file():
        raise FileNotFoundError(f"Extracted json file not found: {extracted_file}")

    with extracted_file.open(encoding="utf-8") as file:
        for line in file:
            record = json.loads(line)
            page = record["page"]
            text = record["text"]
            normalized = re.sub(r"\s+", " ", text)

            matches = [
                target.pattern
                for target in TARGETS
                if target.search(normalized)
            ]

            if matches:
                print(f"\n--- PDF page {page} ---")
                print(f"Matches: {', '.join(matches)}")
                print(normalized[:1800])
