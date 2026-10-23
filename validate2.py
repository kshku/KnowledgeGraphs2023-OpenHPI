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

passages = set(graph.subjects(RDF.type, legal.TextPassage))

empty_passages = []
missing_pages = []

for passage in passages:
    passage_text = list(graph.objects(passage, legal.text))
    page_numbers = list(graph.objects(passage, legal.pageNumber))

    if not passage_text or not str(passage_text[0]).strip():
        empty_passages.append(passage)

    if not page_numbers:
        missing_pages.append(passage)

print("Text passages:", len(passages))
print(
    "Provision-passage links:",
    sum(1 for _ in graph.triples(
        (None, legal.containsPassage, None)
    )),
)
print("Empty passages:", len(empty_passages))
print("Passages without page numbers:", len(missing_pages))

mentions = set(graph.subjects(RDF.type, legal.ReferenceMention))

print("Reference mentions:", len(mentions))
print(
    "Mentions with source passages:",
    len(set(graph.subjects(legal.occursIn, None))),
)
print(
    "Mentions linked to provisions:",
    len(set(graph.subjects(legal.referencesProvision, None))),
)

for mention in sorted(mentions, key=str):
    reference_text = next(
        graph.objects(mention, legal.referenceText), None
    )
    status = next(
        graph.objects(mention, legal.resolutionStatus), None
    )
    target = next(
        graph.objects(mention, legal.referencesProvision), None
    )

    if target is None or status != "resolved":
        print(
            f"{mention.split('#')[-1]}: "
            f"text={reference_text!s}, status={status}, target={target}"
        )
