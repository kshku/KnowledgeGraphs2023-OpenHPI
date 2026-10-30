import json

import pytest

from knowledgegraphs2023_openhpi.documents import (
    Document,
    get_document,
    load_documents,
)


EXPECTED_DOCUMENTS = {
    "railways-act-1989": ("The Railways Act, 1989", 234),
    "multimodal-transportation-of-goods-act-1993": (
        "The Multimodal Transportation of Goods Act, 1993",
        33,
    ),
    "competition-act-2002": ("The Competition Act, 2002", 97),
    "food-safety-and-standards-act-2006": (
        "The Food Safety and Standards Act, 2006",
        101,
    ),
    "legal-metrology-act-2009": ("The Legal Metrology Act, 2009", 57),
    "bureau-of-indian-standards-act-2016": (
        "The Bureau of Indian Standards Act, 2016",
        43,
    ),
    "consumer-protection-act-2019": (
        "The Consumer Protection Act, 2019",
        107,
    ),
    "jammu-and-kashmir-reorganisation-act-2019": (
        "The Jammu and Kashmir Reorganisation Act, 2019",
        107,
    ),
    "mediation-act-2023": ("The Mediation Act, 2023", 65),
}


def test_loads_all_manifest_documents_and_paths():
    documents = load_documents()

    assert len(documents) == 9
    assert {document.id for document in documents} == set(EXPECTED_DOCUMENTS)

    for document in documents:
        title, expected_sections = EXPECTED_DOCUMENTS[document.id]
        assert document.title == title
        assert document.expected_sections == expected_sections
        assert document.pdf_path.is_absolute()
        assert document.pdf_path.is_file()


def test_optional_source_urls_and_get_document():
    documents = load_documents()

    consumer_act = get_document("consumer-protection-act-2019", documents)
    assert consumer_act.source_url.startswith("https://indiacode.gov.in/")
    assert get_document("railways-act-1989", documents).source_url is None
    assert get_document("railways-act-1989", documents) == documents[0]

    with pytest.raises(ValueError, match="Unknown document ID"):
        get_document("unknown-act", documents)


def test_loader_rejects_duplicate_document_ids(tmp_path):
    manifest = {
        "documents": [
            {
                "id": "example-act-2000",
                "title": "Example Act",
                "pdf": "data/example.pdf",
                "expected_sections": 1,
            },
            {
                "id": "example-act-2000",
                "title": "Duplicate Act",
                "pdf": "data/duplicate.pdf",
                "expected_sections": 1,
            },
        ]
    }
    path = tmp_path / "documents.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate document ID"):
        load_documents(path)


def test_loader_resolves_absolute_pdf_and_optional_parser_hints(tmp_path):
    pdf_path = tmp_path / "example.pdf"
    pdf_path.touch()
    manifest = {
        "documents": [
            {
                "id": "example-act-2000",
                "title": " Example Act ",
                "pdf": str(pdf_path),
                "expected_sections": 1,
                "first_section_pattern": "^1\\.",
                "section_pattern": "^(?P<section_id>\\d+[A-Z]?)\\.",
                "end_marker": "^SCHEDULE$",
            }
        ]
    }
    path = tmp_path / "documents.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    [document] = load_documents(path)

    assert isinstance(document, Document)
    assert document.title == "Example Act"
    assert document.pdf_path == pdf_path
    assert document.first_section_pattern == "^1\\."
    assert document.section_pattern == "^(?P<section_id>\\d+[A-Z]?)\\."
    assert document.end_marker == "^SCHEDULE$"


@pytest.mark.parametrize("expected_sections", [0, -1, True, "2"])
def test_loader_rejects_invalid_expected_section_count(
    tmp_path, expected_sections
):
    manifest = {
        "documents": [
            {
                "id": "example-act-2000",
                "title": "Example Act",
                "pdf": "data/example.pdf",
                "expected_sections": expected_sections,
            }
        ]
    }
    path = tmp_path / "documents.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="positive expected_sections"):
        load_documents(path)
