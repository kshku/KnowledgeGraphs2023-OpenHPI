"""Validate the parsed sections and the generated RDF graph."""

import json
from pathlib import Path

from rdflib import Namespace
from rdflib.namespace import RDF

from knowledgegraphs2023_openhpi import config
from knowledgegraphs2023_openhpi.kg import KnowledgeGraph

LEGAL = Namespace(f"{config.ONTOLOGY_IRI}#")
PARSED_PATH = config.PARSED_DIR / "A2019-35.jsonl"


def main() -> None:
    sections = json.loads(Path(PARSED_PATH).read_text(encoding="utf-8"))
    numbers = [section["number"] for section in sections]

    duplicates = sorted(
        {number for number in numbers if numbers.count(number) > 1}
    )
    missing = sorted(
        set(range(1, config.EXPECTED_SECTION_COUNT + 1)) - set(numbers)
    )
    empty = [
        section["number"]
        for section in sections
        if not section["text"].strip()
    ]

    kg = KnowledgeGraph(config.GENERATED_ONTOLOGY_PATH)

    provisions = kg.list_sections()
    passages = set(
        kg.graph.subjects(RDF.type, LEGAL.TextPassage)
    )
    mentions = set(
        kg.graph.subjects(RDF.type, LEGAL.ReferenceMention)
    )

    statuses = {"resolved": 0, "external": 0, "unresolved": 0}

    for mention in mentions:
        status = kg.graph.value(mention, LEGAL.resolutionStatus)
        key = str(status) if status is not None else "unresolved"
        statuses[key] = statuses.get(key, 0) + 1

    print(f"Sections parsed: {len(sections)}")
    print(f"Duplicate section numbers: {duplicates}")
    print(f"Missing section numbers: {missing}")
    print(f"Empty sections: {empty}")
    print(f"Provisions in graph: {len(provisions)}")
    print(f"Text passages: {len(passages)}")
    print(f"Reference mentions: {len(mentions)}")
    print(f"Reference statuses: {statuses}")

    problems = []
    if len(sections) != config.EXPECTED_SECTION_COUNT:
        problems.append("section count")
    if duplicates or missing or empty:
        problems.append("parsed section data")
    if len(provisions) != config.EXPECTED_SECTION_COUNT:
        problems.append("provision count")
    if len(passages) != config.EXPECTED_SECTION_COUNT:
        problems.append("passage count")

    if problems:
        print(f"INVALID: {', '.join(problems)}")
        raise SystemExit(1)

    print("VALID")


if __name__ == "__main__":
    main()
