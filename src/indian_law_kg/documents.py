import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from . import config

DOCUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    pdf_path: Path
    source_url: str | None
    expected_sections: int
    first_section_pattern: str | None = None
    section_pattern: str | None = None
    end_marker: str | None = None


def load_documents(path: Path = config.DOCUMENTS_PATH) -> list[Document]:
    """Load and validate the legal-document manifest."""
    manifest_path = Path(path)

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Document manifest not found: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid document manifest: {exc}") from exc

    if not isinstance(manifest, dict) or not isinstance(
        manifest.get("documents"), list
    ):
        raise ValueError("Document manifest must contain a 'documents' list")

    documents = []
    seen_ids = set()

    for index, item in enumerate(manifest["documents"], start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Document entry {index} must be an object")

        document_id = item.get("id")
        if not isinstance(document_id, str) or not DOCUMENT_ID_PATTERN.fullmatch(
            document_id
        ):
            raise ValueError(
                f"Document entry {index} has an invalid ID: {document_id!r}"
            )

        if document_id in seen_ids:
            raise ValueError(f"Duplicate document ID: {document_id}")
        seen_ids.add(document_id)

        title = item.get("title")
        pdf = item.get("pdf")
        expected_sections = item.get("expected_sections")

        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"Document {document_id} requires a non-empty title")
        if not isinstance(pdf, str) or not pdf.strip():
            raise ValueError(f"Document {document_id} requires a PDF path")
        if (
            not isinstance(expected_sections, int)
            or isinstance(expected_sections, bool)
            or expected_sections < 1
        ):
            raise ValueError(
                f"Document {document_id} requires a positive expected_sections count"
            )

        pdf_path = Path(pdf)
        if not pdf_path.is_absolute():
            pdf_path = config.PROJECT_ROOT / pdf_path

        source_url = item.get("source_url") or None
        if source_url is not None and not isinstance(source_url, str):
            raise ValueError(f"Document {document_id} source_url must be a string")

        hints = {}
        for key in (
            "first_section_pattern",
            "section_pattern",
            "end_marker",
        ):
            value = item.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"Document {document_id} {key} must be a string")
            hints[key] = value

        documents.append(
            Document(
                id=document_id,
                title=title.strip(),
                pdf_path=pdf_path,
                source_url=source_url,
                expected_sections=expected_sections,
                **hints,
            )
        )

    return documents


def get_document(
    document_id: str, documents: Sequence[Document]
) -> Document:
    for document in documents:
        if document.id == document_id:
            return document

    raise ValueError(f"Unknown document ID: {document_id}")
