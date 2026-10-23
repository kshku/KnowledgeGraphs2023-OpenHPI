from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF

path = "ontology/generated/consumer-protection-individuals.rdf"

graph = Graph()
graph.parse(path, format="xml")

legal = Namespace("https://example.org/legal-ontology#")
data_ontology = URIRef(
    "https://example.org/legal-ontology/data/consumer-protection-2019"
)
schema_ontology = URIRef("https://example.org/legal-ontology")

provisions = set(graph.subjects(RDF.type, legal.Provision))
act = legal.ConsumerProtectionAct2019
linked_provisions = set(graph.objects(act, legal.hasProvision))

print("Triples:", len(graph))
print("Provision individuals:", len(provisions))
print("Act hasProvision links:", len(linked_provisions))
print(
    "Missing provision links:",
    len(provisions - linked_provisions),
)
print(
    "Unexpected provision links:",
    len(linked_provisions - provisions),
)
print(
    "Schema import declared:",
    (data_ontology, OWL.imports, schema_ontology) in graph,
)

expected = {
    legal[f"CPA2019_Section{i}"]
    for i in range(1, 108)
}

print("Missing sections:", len(expected - provisions))
print("Unexpected sections:", len(provisions - expected))
