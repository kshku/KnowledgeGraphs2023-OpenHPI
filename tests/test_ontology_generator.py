import pytest
from rdflib import Literal, Namespace
from rdflib.namespace import RDF, XSD

from knowledgegraphs2023_openhpi import config
from knowledgegraphs2023_openhpi.documents import Document
from knowledgegraphs2023_openhpi.ontology_generator import generate_ontology

LEGAL = Namespace(f"{config.ONTOLOGY_IRI}#")


def document(document_id, title, expected_sections, source_url=None):
    return Document(
        id=document_id,
        title=title,
        pdf_path=config.DATA_DIR / "unused.pdf",
        source_url=source_url,
        expected_sections=expected_sections,
    )


def section(section_id, title, text="", page=1):
    return {
        "section_id": section_id,
        "title": title,
        "text": text,
        "start_page": page,
        "end_page": page,
    }


def test_generates_document_scoped_resources_and_exact_reference_links():
    act_a = document("act-a", "The First Act", 3, "https://example.org/a")
    act_b = document("act-b", "The Second Act", 2)
    sections_a = [
        section("2", "Definitions", "See sections 2A and 53-O."),
        section("2A", "Inserted section", "See section 99."),
        section("53-O", "Procedure and powers"),
    ]
    sections_b = [
        section("2", "Other definitions"),
        section("99", "Only in the second Act"),
    ]

    graph = generate_ontology(
        [(act_a, sections_a), (act_b, sections_b)]
    )

    act_a_section_2 = LEGAL["act-a_Section2"]
    act_b_section_2 = LEGAL["act-b_Section2"]
    assert act_a_section_2 != act_b_section_2
    assert (LEGAL["act-a"], RDF.type, LEGAL.Act) in graph
    assert str(graph.value(LEGAL["act-a"], LEGAL.title)) == "The First Act"
    assert (
        act_a_section_2,
        LEGAL.sectionNumber,
        Literal("2", datatype=XSD.string),
    ) in graph
    assert (
        LEGAL["act-a_Section53-O"],
        LEGAL.sectionNumber,
        Literal("53-O", datatype=XSD.string),
    ) in graph

    reference_to_2a = LEGAL["act-a_Section2_Reference1"]
    reference_to_53o = LEGAL["act-a_Section2_Reference2"]
    assert (
        reference_to_2a,
        LEGAL.referencesProvision,
        LEGAL["act-a_Section2A"],
    ) in graph
    assert (
        reference_to_53o,
        LEGAL.referencesProvision,
        LEGAL["act-a_Section53-O"],
    ) in graph
    assert (
        LEGAL["act-a_Section2A_Reference1"],
        LEGAL.resolutionStatus,
        Literal("unresolved", datatype=XSD.string),
    ) in graph
    assert (
        LEGAL["act-a_Section2A_Reference1"],
        LEGAL.referencesProvision,
        LEGAL["act-b_Section99"],
    ) not in graph
    assert (
        LEGAL["act-a"],
        LEGAL.sourceURL,
        Literal(
            "https://example.org/a", datatype=XSD.anyURI
        ),
    ) in graph


def test_generation_is_deterministic(tmp_path):
    doc = document("act-a", "The First Act", 1)
    inputs = [(doc, [section("2A", "Inserted section")])]

    first = generate_ontology(inputs)
    second = generate_ontology(inputs)
    first_path = tmp_path / "first.rdf"
    second_path = tmp_path / "second.rdf"
    first.serialize(destination=first_path, format="xml")
    second.serialize(destination=second_path, format="xml")

    assert first_path.read_bytes() == second_path.read_bytes()


def test_generation_rejects_duplicate_ids_and_wrong_counts():
    doc = document("act-a", "The First Act", 2)

    with pytest.raises(ValueError, match="duplicate section IDs"):
        generate_ontology(
            [
                (
                    doc,
                    [section("2A", "First"), section("2A", "Duplicate")],
                )
            ]
        )

    with pytest.raises(ValueError, match="expected 2 sections, got 1"):
        generate_ontology([(doc, [section("2A", "Only one")])])
