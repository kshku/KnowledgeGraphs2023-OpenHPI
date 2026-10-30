import pytest


def test_list_documents(kg):
    assert kg.list_documents() == [
        {
            "document_id": "example-act-a",
            "title": "Example Act A",
            "source_url": "https://example.org/a",
            "section_count": 3,
        },
        {
            "document_id": "example-act-b",
            "title": "Example Act B",
            "source_url": None,
            "section_count": 2,
        },
    ]


def test_list_sections_includes_document_identity_and_string_ids(kg):
    sections = kg.list_sections()

    assert [
        (section["document_id"], section["section_id"])
        for section in sections
    ] == [
        ("example-act-a", "2"),
        ("example-act-a", "2A"),
        ("example-act-a", "53-O"),
        ("example-act-b", "2"),
        ("example-act-b", "99"),
    ]
    assert sections[0]["document_title"] == "Example Act A"
    assert sections[0]["title"] == "Definitions"
    assert [
        section["section_id"]
        for section in kg.list_sections("example-act-a")
    ] == ["2", "2A", "53-O"]


def test_get_section_is_document_scoped_and_unknown_section_is_none(kg):
    section = kg.get_section("53-O", "example-act-a")
    assert section["document_title"] == "Example Act A"
    assert section["section_id"] == "53-O"
    assert section["title"] == "Procedure and powers"
    assert section["text"] == "53-O. Procedure and powers.—Body for 53-O."
    assert section["start_page"] == 8
    assert kg.get_section("99", "example-act-a") is None
    assert kg.get_section("99", "example-act-b")["title"] == "Only in Act B"


def test_section_addressed_calls_require_document_when_ambiguous(kg):
    with pytest.raises(ValueError, match="document_id is required"):
        kg.get_section("2")
    with pytest.raises(ValueError, match="document_id is required"):
        kg.section_exists("2")
    with pytest.raises(ValueError, match="Unknown document ID"):
        kg.get_section("2", "unknown-act")


def test_references_resolve_only_within_the_document(kg):
    references = kg.get_references("2", "example-act-a")

    assert [reference["target"] for reference in references] == [
        "2A",
        "53-O",
        None,
    ]
    assert [reference["status"] for reference in references] == [
        "resolved",
        "resolved",
        "unresolved",
    ]
    assert kg.get_referenced_by("2", "example-act-a") == ["2A"]
    assert kg.get_referenced_by("2A", "example-act-a") == ["2"]
    assert kg.get_external_references("2", "example-act-a") == []


def test_get_schema(kg):
    schema = kg.get_schema()

    assert schema["schema_loaded"] is True
    assert schema["prefixes"]["legal"] == "https://example.org/legal-ontology#"
    assert "Provision" in schema["classes"]
    assert {
        "name": "containsPassage",
        "domain": "Provision",
        "range": "TextPassage",
    } in schema["object_properties"]
    assert {
        "name": "sectionNumber",
        "domain": "Provision",
        "range": "string",
    } in schema["datatype_properties"]
    assert schema["counts"] == {
        "provisions": 5,
        "text_passages": 5,
        "reference_mentions": 4,
    }


def test_missing_schema_is_reported(monkeypatch, tmp_path, kg):
    monkeypatch.setattr(
        "knowledgegraphs2023_openhpi.kg.config.ONTOLOGY_SCHEMA_PATH",
        tmp_path / "missing.rdf",
    )

    path = tmp_path / "kg.rdf"
    kg.graph.serialize(destination=path, format="xml")

    schema = type(kg)(path).get_schema()

    assert schema["schema_loaded"] is False
    assert schema["classes"] == []
    assert schema["counts"]["provisions"] == 5


def test_find_sections_searches_all_documents_and_can_filter(kg):
    matches = kg.find_sections("definitions")
    assert {
        (section["document_id"], section["section_id"])
        for section in matches
    } == {
        ("example-act-a", "2"),
        ("example-act-a", "2A"),
        ("example-act-b", "2"),
    }
    assert kg.find_sections("definitions", "example-act-b")[0][
        "document_title"
    ] == "Example Act B"
    assert kg.find_sections("no-such-term") == []
    assert kg.find_sections("   ") == []
