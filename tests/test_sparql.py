import pytest
from rdflib import Graph, Literal, Namespace

from knowledgegraphs2023_openhpi.sparql import run_query, validate_read_only

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
