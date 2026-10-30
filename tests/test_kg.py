from knowledgegraphs2023_openhpi.kg import KnowledgeGraph


def test_list_sections(kg):
    assert kg.list_sections() == [
        {"number": 1, "title": "Short title"},
        {"number": 2, "title": "Definitions"},
    ]


def test_get_section_and_unknown(kg):
    section = kg.get_section(2)
    assert section["title"] == "Definitions"
    assert section["text"] == "2. Definitions.—Body two."
    assert section["start_page"] == 7
    assert kg.get_section(999) is None


def test_references(kg):
    [reference] = kg.get_references(1)
    assert reference == {
        "reference_text": "section 2",
        "status": "resolved",
        "target": 2,
        "external_law": None,
    }
    assert kg.get_referenced_by(2) == [1]


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
        "provisions": 2,
        "text_passages": 2,
        "reference_mentions": 1,
    }


def test_missing_schema_is_reported(monkeypatch, tmp_path, kg):
    monkeypatch.setattr(
        "knowledgegraphs2023_openhpi.kg.config.ONTOLOGY_SCHEMA_PATH",
        tmp_path / "missing.rdf",
    )

    path = tmp_path / "kg.rdf"
    kg.graph.serialize(destination=path, format="xml")

    schema = KnowledgeGraph(path).get_schema()

    assert schema["schema_loaded"] is False
    assert schema["classes"] == []
    assert schema["counts"]["provisions"] == 2


def test_find_sections(kg):
    assert [s["number"] for s in kg.find_sections("definitions")] == [2]
    assert kg.find_sections("no-such-term") == []
