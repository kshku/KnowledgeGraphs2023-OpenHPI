import json
import re
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

ONTOLOGY_IRI = "https://example.org/legal-ontology"
DATA_ONTOLOGY_IRI = (
    "https://example.org/legal-ontology/data/consumer-protection-2019"
)

LEGAL = Namespace(f"{ONTOLOGY_IRI}#")

ACT_TITLE = "The Consumer Protection Act, 2019"

ACT_SOURCE_URL = (
    "https://indiacode.gov.in/pdf-viewer/"
    "1b6c1754-47b1-411e-9607-1712a9caf368/"
    "b5ba879f-4662-458c-b5d3-dae377ff92e0"
)

EXPECTED_SECTION_COUNT = 107

EXTERNAL_LAW_PATTERN = re.compile(
    r"^\s*(?:of|under|within the meaning of|as provided by)\s+"
    r"(?:the\s+)?"
    r"(?:First Schedule\s+to\s+)?"
    r"(Indian Penal Code"
    r"|Finance Act(?:\s*,?\s*\d{4})?"
    r"|Food Safety and Standards Act(?:\s*,?\s*\d{4})?"
    r"|Code of Criminal Procedure"
    r"|Code of Civil Procedure"
    r"|Information Technology Act(?:\s*,?\s*\d{4})?"
    r"|Companies Act(?:\s*,?\s*\d{4})?)\b",
    re.IGNORECASE,
)


def extract_references(text: str):
    """Yield (reference_text, target_number, is_external) tuples."""

    pattern = re.compile(
        r"\bsections?\s+(\d+)"
        r"((?:\s*(?:,|and|to)\s*\d+)*)",
        re.IGNORECASE,
    )

    for match in pattern.finditer(text):
        reference_text = match.group(0)

        # Only examine the text immediately after the citation.
        # Do not classify a citation based on a law mentioned elsewhere
        # in the section.
        following_text = text[match.end():match.end() + 120]
        is_external = bool(
            EXTERNAL_LAW_PATTERN.search(following_text)
        )

        numbers = [int(match.group(1))]
        numbers.extend(
            int(number)
            for number in re.findall(r"\d+", match.group(2))
        )

        for number in numbers:
            yield reference_text, number, is_external


def generate_ontology(sections: list[dict]) -> Graph:
    """Generate individuals for the Act, its provisions, passages and references."""

    graph = Graph()

    graph.bind("legal", LEGAL)
    graph.bind("owl", OWL)
    graph.bind("xsd", XSD)

    # Declare the generated data ontology and its schema import.
    data_ontology = URIRef(DATA_ONTOLOGY_IRI)

    graph.add((data_ontology, RDF.type, OWL.Ontology))
    graph.add((data_ontology, OWL.imports, URIRef(ONTOLOGY_IRI)))

    # Create the Act individual.
    act = LEGAL.ConsumerProtectionAct2019

    graph.add((act, RDF.type, LEGAL.Act))
    graph.add((act, LEGAL.title, Literal(ACT_TITLE, datatype=XSD.string)))
    graph.add(
        (
            act,
            LEGAL.sourceURL,
            Literal(ACT_SOURCE_URL, datatype=XSD.anyURI),
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

        for index, (reference_text, target_number, is_external) in enumerate(
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
                    Literal(reference_text, datatype=XSD.string),
                )
            )
            graph.add((mention, LEGAL.occursIn, passage))

            # An explicitly identified external law takes priority over
            # the numeric range check.
            if is_external:
                status = "external"

            elif 1 <= target_number <= EXPECTED_SECTION_COUNT:
                target = LEGAL[f"CPA2019_Section{target_number}"]
                graph.add((mention, LEGAL.referencesProvision, target))
                status = "resolved"

            else:
                status = "unresolved"

            graph.add(
                (
                    mention,
                    LEGAL.resolutionStatus,
                    Literal(status, datatype=XSD.string),
                )
            )

    # Check that the parser supplied the expected set of sections.
    expected_numbers = set(range(1, EXPECTED_SECTION_COUNT + 1))

    if seen_numbers != expected_numbers:
        missing = sorted(expected_numbers - seen_numbers)
        unexpected = sorted(seen_numbers - expected_numbers)

        raise ValueError(
            f"Unexpected section set. "
            f"Missing: {missing}; unexpected: {unexpected}"
        )

    return graph


def main():
    with INPUT_PATH.open("r", encoding="utf-8") as file:
        sections = json.load(file)

    graph = generate_ontology(sections)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(OUTPUT_PATH), format="xml")

    print(f"Sections processed: {len(sections)}")
    print(f"RDF triples generated: {len(graph)}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

