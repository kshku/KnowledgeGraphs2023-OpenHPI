from knowledgegraphs2023_openhpi.references import (
    Reference,
    extract_references,
    resolution_status,
)


def test_single_internal_reference():
    [ref] = list(extract_references("as provided under section 10 of this Act"))
    assert ref == Reference("section 10", 10, False, None)


def test_list_of_references():
    refs = list(extract_references("sections 2, 3 and 4 shall apply"))
    assert [r.target for r in refs] == [2, 3, 4]


def test_range_is_expanded():
    refs = list(extract_references("sections 2 to 5 shall apply"))
    assert [r.target for r in refs] == [2, 3, 4, 5]


def test_external_law_is_classified():
    [ref] = list(extract_references("section 10 of the Indian Penal Code"))
    assert ref.is_external is True
    assert ref.external_law == "Indian Penal Code"


def test_resolution_status():
    assert resolution_status(Reference("section 2", 2, False, None)) == "resolved"
    assert resolution_status(Reference("section 200", 200, False, None)) == "unresolved"
    assert (
        resolution_status(Reference("section 10", 10, True, "Indian Penal Code"))
        == "external"
    )
