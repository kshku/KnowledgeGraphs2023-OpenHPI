import json
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, XSD


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = PROJECT_ROOT / "data" / "parsed" / "A2019-35.jsonl"
OUTPUT_PATH = (
    PROJECT_ROOT
    / "ontology"
    / "generated"
    / "consumer-protection-individuals.rdf"
)

# The ontology containing your manually defined classes and properties.
ONTOLOGY_IRI = "https://example.org/legal-ontology"

# Give the generated data ontology its own IRI.
DATA_ONTOLOGY_IRI = (
    "https://example.org/legal-ontology/data/consumer-protection-2019"
)

# Assumes entity IRIs use the # separator. Verify this in Protégé.
LEGAL = Namespace(f"{ONTOLOGY_IRI}#")


def load_sections(path: Path) -> list[dict]:
    """Load the parsed sections produced by the existing parser."""
    with path.open(encoding="utf-8") as file:
        sections = json.load(file)

    if not isinstance(sections, list):
        raise ValueError("Expected the parsed file to contain a JSON array.")

    return sections


def generate_ontology(sections: list[dict]) -> Graph:
    graph = Graph()

    graph.bind("legal", LEGAL)
    graph.bind("owl", OWL)
    graph.bind("xsd", XSD)

    # Declare this as a separate ontology document.
    data_ontology = URIRef(DATA_ONTOLOGY_IRI)
    graph.add((data_ontology, RDF.type, OWL.Ontology))

    graph.add((
        data_ontology,
        OWL.imports,
        URIRef(ONTOLOGY_IRI),
    ))

    # Create the Act individual.
    act = LEGAL.ConsumerProtectionAct2019
    graph.add((act, RDF.type, LEGAL.Act))
    graph.add((
        act,
        LEGAL.title,
        Literal("The Consumer Protection Act, 2019", datatype=XSD.string),
    ))
    graph.add((
        act,
        LEGAL.sourceURL,
        Literal(
            "https://indiacode.gov.in/pdf-viewer/"
            "1b6c1754-47b1-411e-9607-1712a9caf368/"
            "b5ba879f-4662-458c-b5d3-dae377ff92e0",
            datatype=XSD.anyURI,
        ),
    ))

    seen_numbers: set[int] = set()

    for section in sections:
        number = int(section["number"])

        if number in seen_numbers:
            raise ValueError(f"Duplicate section number: {number}")
        seen_numbers.add(number)

        provision = LEGAL[f"CPA2019_Section{number}"]

        graph.add((provision, RDF.type, LEGAL.Provision))
        graph.add((
            provision,
            LEGAL.sectionNumber,
            Literal(str(number), datatype=XSD.string),
        ))
        graph.add((
            provision,
            LEGAL.sectionTitle,
            Literal(section["title"], datatype=XSD.string),
        ))
        graph.add((act, LEGAL.hasProvision, provision))

    if len(seen_numbers) != len(sections):
        raise ValueError("Some section records were not uniquely represented.")

    return graph


def main() -> None:
    sections = load_sections(INPUT_PATH)
    graph = generate_ontology(sections)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(OUTPUT_PATH), format="xml")

    print(f"Sections processed: {len(sections)}")
    print(f"RDF triples generated: {len(graph)}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

