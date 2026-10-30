import pytest
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from knowledgegraphs2023_openhpi.config import ONTOLOGY_IRI
from knowledgegraphs2023_openhpi.kg import KnowledgeGraph

LEGAL = Namespace(f"{ONTOLOGY_IRI}#")


@pytest.fixture
def kg(tmp_path):
    graph = Graph()
    act = LEGAL.ConsumerProtectionAct2019

    sections = [
        (1, "Short title", "1. Short title.—Body one.", 6),
        (2, "Definitions", "2. Definitions.—Body two.", 7),
    ]

    for number, title, text, page in sections:
        provision = LEGAL[f"CPA2019_Section{number}"]
        passage = LEGAL[f"CPA2019_Section{number}_Passage1"]

        graph.add((act, LEGAL.hasProvision, provision))
        graph.add((provision, RDF.type, LEGAL.Provision))
        graph.add(
            (
                provision,
                LEGAL.sectionNumber,
                Literal(str(number), datatype=XSD.string),
            )
        )
        graph.add((provision, LEGAL.sectionTitle, Literal(title)))
        graph.add((provision, LEGAL.containsPassage, passage))
        graph.add((passage, RDF.type, LEGAL.TextPassage))
        graph.add((passage, LEGAL.text, Literal(text)))
        graph.add(
            (
                passage,
                LEGAL.pageNumber,
                Literal(page, datatype=XSD.integer),
            )
        )

    mention = LEGAL["CPA2019_Section1_Reference1"]
    graph.add((mention, RDF.type, LEGAL.ReferenceMention))
    graph.add((mention, LEGAL.referenceText, Literal("section 2")))
    graph.add((mention, LEGAL.resolutionStatus, Literal("resolved")))
    graph.add((mention, LEGAL.occursIn, LEGAL["CPA2019_Section1_Passage1"]))
    graph.add(
        (
            mention,
            LEGAL.referencesProvision,
            LEGAL["CPA2019_Section2"],
        )
    )

    path = tmp_path / "kg.rdf"
    graph.serialize(destination=path, format="xml")
    return KnowledgeGraph(path)
