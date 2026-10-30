import json

import pytest
import pymupdf

from knowledgegraphs2023_openhpi.documents import load_documents
from knowledgegraphs2023_openhpi.parser import parse, parse_sections


def records(*pages):
    return [
        {"page": page_number, "text": text}
        for page_number, text in enumerate(pages, start=1)
    ]


def test_parse_sections_preserves_alphanumeric_ids_and_wrapped_titles():
    sections = parse_sections(
        records(
            "Arrangement of Sections\n"
            "1. Short title and commencement.\n"
            "1. Short title and commencement.—This Act may be called the Act.",
            "2A. Appointment of the Chief Commissioner and other\n"
            "Commissioners.—The Commission shall be established.\n"
            "(2) This subsection belongs to section 2A.",
            "3.Territorial jurisdiction.—The Commission may act.",
        )
    )

    assert [section.section_id for section in sections] == ["1", "2A", "3"]
    assert sections[1].title == (
        "Appointment of the Chief Commissioner and other Commissioners"
    )
    assert "(2) This subsection belongs to section 2A." in sections[1].text
    assert sections[2].title == "Territorial jurisdiction"


def test_parse_sections_strips_amendment_markers_and_skips_numbered_notes():
    sections = parse_sections(
        records(
            "1. Short title.—This Act may be called the Act.\n"
            "2. This is an enumerated item, not a heading.\n"
            "2. Subs. by section 4, for the words.\n"
            "13.Territorial jurisdiction.—The Commission may act.\n"
            "2[33. Tribunal.—The Tribunal shall have jurisdiction."
        )
    )

    assert [section.section_id for section in sections] == ["1", "13", "33"]
    assert sections[1].title == "Territorial jurisdiction"
    assert sections[2].title == "Tribunal"


def test_parse_sections_rejects_duplicate_ids():
    with pytest.raises(ValueError, match="Duplicate section ID: 2A"):
        parse_sections(
            records(
                "1. Short title.—This Act may be called the Act.\n"
                "2A. Inserted provision.—First occurrence.\n"
                "2A. Inserted provision.—Duplicate occurrence."
            )
        )


def test_parse_sections_supports_custom_section_pattern_and_end_marker():
    sections = parse_sections(
        records(
            "1. Short title.—This Act may be called the Act.\n"
            "2A: Definitions.—Terms are defined.\n"
            "SCHEDULE\n"
            "3. This is after the schedule marker.—Not included."
        ),
        section_pattern=(
            r"^\s*(?P<section_id>\d+[A-Z]?)(?:\.|:)\s*"
            r"(?P<remainder>.*)$"
        ),
        end_marker=r"^SCHEDULE\s*$",
    )

    assert [section.section_id for section in sections] == ["1", "2A"]


def test_parse_sections_recognizes_repealed_and_replaced_headings():
    sections = parse_sections(
        records(
            "1. Short title.—This Act may be called the Act.\n"
            "2. Definitions.—Terms are defined.\n"
            "3. [Amendment of certain enactments]. Rep. by another Act.\n"
            "4. Repeal and savings.—The prior law is repealed."
        )
    )

    assert [section.section_id for section in sections] == ["1", "2", "3", "4"]
    assert sections[2].title == "Amendment of certain enactments"


def test_all_manifest_pdfs_parse_expected_provision_counts():
    results = {}

    for document in load_documents():
        with pymupdf.open(document.pdf_path) as pdf:
            page_records = [
                {"page": number, "text": page.get_text("text")}
                for number, page in enumerate(pdf, start=1)
            ]

        sections = parse_sections(
            page_records,
            first_section_pattern=document.first_section_pattern,
            section_pattern=document.section_pattern,
            end_marker=document.end_marker,
        )
        ids = {section.section_id for section in sections}
        assert len(sections) == document.expected_sections, document.id
        assert len(ids) == len(sections), document.id
        results[document.id] = ids

    assert {"34", "35", "158", "176", "4-I", "20-O"} <= results[
        "railways-act-1989"
    ]
    assert {"20A", "31", "32"} <= results[
        "multimodal-transportation-of-goods-act-1993"
    ]
    assert {"53-O", "53-S", "53B"} <= results["competition-act-2002"]
    assert "153-O" not in results["competition-act-2002"]


def test_parse_writes_section_records_as_json_array(tmp_path):
    extracted_path = tmp_path / "pages.jsonl"
    extracted_path.write_text(
        json.dumps(
            {
                "page": 1,
                "text": "1. Short title.—This Act may be called the Act.\n"
                "2A. Definitions.—A definition.",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    parsed_path = tmp_path / "parsed" / "example-act.json"

    sections = parse(extracted_path, parsed_path)

    assert [section.section_id for section in sections] == ["1", "2A"]
    parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    assert [section["section_id"] for section in parsed] == ["1", "2A"]
    assert parsed[1]["title"] == "Definitions"
