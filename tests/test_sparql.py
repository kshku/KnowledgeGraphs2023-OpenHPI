import pytest
from rdflib import Graph, Literal, Namespace

from indian_law_kg.sparql import (
    run_ask,
    run_query,
    run_select,
    validate_read_only,
)

LEGAL = Namespace("https://example.org/legal-ontology#")


def test_rejects_updates():
    for query in [
        "DELETE WHERE { ?s ?p ?o }",
        "INSERT DATA { <a> <b> <c> }",
        "LOAD <http://example.org/x>",
        "WITH <g> DELETE { ?s ?p ?o } WHERE { ?s ?p ?o }",
    ]:
        with pytest.raises(ValueError):
            validate_read_only(query)


def test_rejects_empty():
    with pytest.raises(ValueError):
        validate_read_only("   ")


def test_rejects_network_queries():
    for query in [
        "SELECT * WHERE { SERVICE <http://example.org/sparql> "
        "{ ?s ?p ?o } }",
        "SELECT * FROM <http://example.org/data> WHERE { ?s ?p ?o }",
    ]:
        with pytest.raises(ValueError, match="not allowed"):
            validate_read_only(query)


def test_select_runs():
    graph = Graph()
    graph.add((LEGAL.Provision1, LEGAL.sectionNumber, Literal("1")))

    result = run_query(
        graph,
        "SELECT ?n WHERE { "
        "?s <https://example.org/legal-ontology#sectionNumber> ?n }",
    )

    assert result["columns"] == ["n"]
    assert result["rows"] == [{"n": "1"}]


def test_ask_runs():
    graph = Graph()
    graph.add((LEGAL.Provision1, LEGAL.sectionNumber, Literal("1")))

    result = run_query(graph, "ASK { ?s ?p ?o }")

    assert result == {"ask": True}


def test_run_select_returns_bound_result_rows():
    graph = Graph()
    expected = 'literal with " quote } UNION { ?s ?p ?o'
    graph.add((LEGAL.Provision1, LEGAL.sectionTitle, Literal(expected)))
    graph.add((LEGAL.Provision2, LEGAL.sectionTitle, Literal("another title")))

    rows = run_select(
        graph,
        "SELECT ?title WHERE { "
        "?provision <https://example.org/legal-ontology#sectionTitle> ?title . "
        "FILTER(?title = ?needle) }",
        {"needle": Literal(expected)},
    )

    assert rows == [{"title": expected}]


def test_run_ask_supports_bindings():
    graph = Graph()
    graph.add((LEGAL.Provision1, LEGAL.sectionNumber, Literal("53-O")))

    assert run_ask(
        graph,
        "ASK { ?provision <https://example.org/legal-ontology#sectionNumber> "
        "?section_id }",
        {"section_id": Literal("53-O")},
    ) is True


def test_bound_helpers_enforce_read_only_query_forms():
    graph = Graph()

    with pytest.raises(ValueError, match="INSERT is not allowed"):
        run_select(
            graph,
            "SELECT * WHERE { ?s ?p ?o } INSERT DATA { <urn:s> <urn:p> <urn:o> }",
        )
    with pytest.raises(ValueError, match="SERVICE is not allowed"):
        run_ask(graph, "ASK { SERVICE <https://example.org/sparql> { ?s ?p ?o } }")


def test_helpers_reject_wrong_query_form():
    graph = Graph()

    with pytest.raises(ValueError, match="requires a SPARQL SELECT"):
        run_select(graph, "ASK { ?s ?p ?o }")
    with pytest.raises(ValueError, match="requires a SPARQL ASK"):
        run_ask(graph, "SELECT * WHERE { ?s ?p ?o }")
