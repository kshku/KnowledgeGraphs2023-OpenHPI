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


def test_find_sections(kg):
    assert [s["number"] for s in kg.find_sections("definitions")] == [2]
    assert kg.find_sections("no-such-term") == []
