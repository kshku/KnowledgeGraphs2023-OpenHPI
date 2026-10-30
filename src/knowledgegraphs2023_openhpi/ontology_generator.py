import json

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, XSD

from . import config
from .references import extract_references, resolution_status

LEGAL = Namespace(f"{config.ONTOLOGY_IRI}#")


def generate_ontology(sections: list[dict]) -> Graph:
    """Generate individuals for the Act, provisions, passages and references."""

    graph = Graph()

    graph.bind("legal", LEGAL)
    graph.bind("owl", OWL)
    graph.bind("xsd", XSD)

    # Declare the generated data ontology and its schema import.
    data_ontology = URIRef(config.DATA_ONTOLOGY_IRI)

    graph.add((data_ontology, RDF.type, OWL.Ontology))
    graph.add((data_ontology, OWL.imports, URIRef(config.ONTOLOGY_IRI)))

    act = LEGAL.ConsumerProtectionAct2019

    graph.add((act, RDF.type, LEGAL.Act))
    graph.add(
        (act, LEGAL.title, Literal(config.ACT_TITLE, datatype=XSD.string))
    )
    graph.add(
        (
            act,
            LEGAL.sourceURL,
            Literal(config.ACT_SOURCE_URL, datatype=XSD.anyURI),
        )
    )

    seen_numbers = set()

    # First pass: create provisions and their text passages.
    for section in sections:
        number = int(section["number"])

        if number in seen_numbers:
            raise ValueError(f"Duplicate section number: {number}")

        seen_numbers.add(number)

        provision = LEGAL[f"CPA2019_Section{number}"]
        passage = LEGAL[f"CPA2019_Section{number}_Passage1"]

        graph.add((provision, RDF.type, LEGAL.Provision))
        graph.add(
            (
                provision,
                LEGAL.sectionNumber,
                Literal(str(number), datatype=XSD.string),
            )
        )
        graph.add(
            (
                provision,
                LEGAL.sectionTitle,
                Literal(section["title"], datatype=XSD.string),
            )
        )

        graph.add((act, LEGAL.hasProvision, provision))

        graph.add((passage, RDF.type, LEGAL.TextPassage))
        graph.add(
            (
                passage,
                LEGAL.text,
                Literal(section["text"], datatype=XSD.string),
            )
        )
        graph.add(
            (
                passage,
                LEGAL.pageNumber,
                Literal(int(section["start_page"]), datatype=XSD.integer),
            )
        )

        graph.add((provision, LEGAL.containsPassage, passage))

    # Second pass: extract references after all target provisions exist.
    for section in sections:
        source_number = int(section["number"])
        passage = LEGAL[f"CPA2019_Section{source_number}_Passage1"]

        for index, reference in enumerate(
            extract_references(section["text"]),
            start=1,
        ):
            mention = LEGAL[
                f"CPA2019_Section{source_number}_Reference{index}"
            ]

            graph.add((mention, RDF.type, LEGAL.ReferenceMention))
            graph.add(
                (
                    mention,
                    LEGAL.referenceText,
                    Literal(reference.text, datatype=XSD.string),
                )
            )
            graph.add((mention, LEGAL.occursIn, passage))

            status = resolution_status(
                reference, config.EXPECTED_SECTION_COUNT
            )

            if status == "resolved":
                target = LEGAL[f"CPA2019_Section{reference.target}"]
                graph.add((mention, LEGAL.referencesProvision, target))

            elif status == "external" and reference.external_law:
                graph.add(
                    (
                        mention,
                        LEGAL.externalLaw,
                        Literal(reference.external_law, datatype=XSD.string),
                    )
                )

            graph.add(
                (
                    mention,
                    LEGAL.resolutionStatus,
                    Literal(status, datatype=XSD.string),
                )
            )

    # Check that the parser supplied the expected set of sections.
    expected_numbers = set(range(1, config.EXPECTED_SECTION_COUNT + 1))

    if seen_numbers != expected_numbers:
        missing = sorted(expected_numbers - seen_numbers)
        unexpected = sorted(seen_numbers - expected_numbers)

        raise ValueError(
            f"Unexpected section set. "
            f"Missing: {missing}; unexpected: {unexpected}"
        )

    return graph


def main() -> None:
    input_path = config.PARSED_DIR / "A2019-35.jsonl"

    with input_path.open("r", encoding="utf-8") as file:
        sections = json.load(file)

    graph = generate_ontology(sections)

    config.GENERATED_ONTOLOGY_PATH.parent.mkdir(
        parents=True, exist_ok=True
    )
    graph.serialize(
        destination=str(config.GENERATED_ONTOLOGY_PATH), format="xml"
    )

    print(f"Sections processed: {len(sections)}")
    print(f"RDF triples generated: {len(graph)}")
    print(f"Output: {config.GENERATED_ONTOLOGY_PATH}")


if __name__ == "__main__":
    main()
