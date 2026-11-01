from knowledgegraphs2023_openhpi.references import (
    Reference,
    extract_references,
    resolution_status,
)


def test_single_internal_reference():
    [ref] = list(extract_references("as provided under section 10 of this Act"))
    assert ref == Reference("section 10", "10", False, None)


def test_list_of_references():
    refs = list(extract_references("sections 2, 3 and 4 shall apply"))
    assert [r.target for r in refs] == ["2", "3", "4"]


def test_range_is_expanded():
    refs = list(extract_references("sections 2 to 5 shall apply"))
    assert [r.target for r in refs] == ["2", "3", "4", "5"]


def test_alphanumeric_and_hyphenated_section_ids_are_preserved():
    refs = list(extract_references("sections 2A, 2B and 53-O shall apply"))

    assert [reference.target for reference in refs] == ["2A", "2B", "53-O"]


def test_external_law_is_classified():
    [ref] = list(extract_references("section 10 of the Indian Penal Code"))
    assert ref.is_external is True
    assert ref.external_law == "Indian Penal Code"


def test_general_clauses_act_is_external():
    [ref] = list(
        extract_references("section 6 of the General Clauses Act, 1897")
    )
    assert ref.is_external is True
    assert ref.external_law == "General Clauses Act, 1897"


def test_external_law_across_line_break():
    [ref] = list(
        extract_references("section 320 of the Indian\nPenal Code")
    )
    assert ref.is_external is True
    assert ref.external_law == "Indian Penal Code"


def test_external_law_after_chapter_mention():
    [ref] = list(
        extract_references(
            "section 195 and Chapter XXVI of the Code of Criminal "
            "Procedure"
        )
    )
    assert ref.is_external is True
    assert ref.external_law == "Code of Criminal Procedure"


def test_resolution_status():
    section_ids = {"2", "2A", "53-O"}
    assert resolution_status(
        Reference("section 2", "2", False, None), section_ids
    ) == "resolved"
    assert resolution_status(
        Reference("section 2A", "2A", False, None), section_ids
    ) == "resolved"
    assert resolution_status(
        Reference("section 53-O", "53-O", False, None), section_ids
    ) == "resolved"
    assert resolution_status(
        Reference("section 200", "200", False, None), section_ids
    ) == "unresolved"
    assert (
        resolution_status(
            Reference("section 10", "10", True, "Indian Penal Code"),
            section_ids,
        )
        == "external"
    )
