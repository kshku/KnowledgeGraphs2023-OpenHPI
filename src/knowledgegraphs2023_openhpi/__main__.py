import argparse
from pathlib import Path
import pymupdf

from .pdf_utils import inspect_pdf, extract_pdf, inspect_sections
from .parser import parse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

EXTRACTED_DIR = DATA_DIR / "extracted"
PARSED_DIR = DATA_DIR / "parsed"

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Data extraction and feeding pipeline"
    )
    parser.add_argument(
        "pdf",
        help="PDF file to extract from",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    extracted_json_path = EXTRACTED_DIR / f"{pdf_path.stem}.jsonl"
    parsed_json_path = PARSED_DIR / f"{pdf_path.stem}.jsonl"

    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    try:
        extract_pdf(pdf_path, extracted_json_path)
        # inspect_sections(extracted_json_path)
        parse(extracted_json_path, parsed_json_path)
    except (FileNotFoundError, pymupdf.FileDataError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
