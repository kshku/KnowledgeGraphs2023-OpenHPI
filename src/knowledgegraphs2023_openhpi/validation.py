import json

from rdflib import Namespace
from rdflib.namespace import RDF

from . import config
from .documents import Document, load_documents
from .kg import KnowledgeGraph

LEGAL = Namespace(f"{config.ONTOLOGY_IRI}#")


def validate_parsed_sections(
    document: Document, sections: list[dict]
) -> list[str]:
    problems = []
    section_ids = []

    for index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            problems.append(f"parsed record {index} is not an object")
            continue
        section_id = section.get("section_id")
        if not isinstance(section_id, str) or not section_id.strip():
            problems.append(f"parsed record {index} has an empty/invalid section ID")
            continue
        section_ids.append(section_id)
        if not str(section.get("text", "")).strip():
            problems.append(f"section {section_id} has empty text")

    duplicates = sorted(
        {item for item in section_ids if section_ids.count(item) > 1}
    )
    if duplicates:
        problems.append(f"duplicate section IDs: {duplicates}")
    if len(sections) != document.expected_sections:
        problems.append(
            f"expected {document.expected_sections} parsed sections, got {len(sections)}"
        )
    return problems


def validate_document(
    document: Document, sections: list[dict], kg: KnowledgeGraph
) -> list[str]:
    """Compare one document's parsed records against its RDF individuals."""
    problems = validate_parsed_sections(document, sections)
    graph_document = next(
        (item for item in kg.list_documents() if item["document_id"] == document.id),
        None,
    )
    if graph_document is None:
        return problems + ["Act individual is missing from the RDF graph"]
    if graph_document["title"] != document.title:
        problems.append(f"RDF Act title mismatch: {graph_document['title']!r}")
    if document.source_url and graph_document["source_url"] != document.source_url:
        problems.append("RDF source URL does not match the manifest")
    if graph_document["section_count"] != document.expected_sections:
        problems.append(
            f"expected {document.expected_sections} RDF provisions, "
            f"got {graph_document['section_count']}"
        )

    valid_sections = [
        item
        for item in sections
        if isinstance(item, dict)
        and isinstance(item.get("section_id"), str)
        and item["section_id"].strip()
    ]
    parsed_ids = {item["section_id"] for item in valid_sections}
    graph_sections = kg.list_sections(document.id)
    graph_ids = {item["section_id"] for item in graph_sections}
    if parsed_ids != graph_ids:
        problems.append(
            "parsed/RDF section ID mismatch: "
            f"missing in RDF={sorted(parsed_ids - graph_ids)}, "
            f"extra in RDF={sorted(graph_ids - parsed_ids)}"
        )

    act = LEGAL[document.id]
    expected_prefix = f"{document.id}_Section"
    for linked_provision in kg.graph.objects(act, LEGAL.hasProvision):
        local_name = str(linked_provision).rsplit("#", 1)[-1]
        if not local_name.startswith(expected_prefix):
            problems.append(
                f"Act is linked to a foreign provision: {local_name}"
            )

    for section in valid_sections:
        section_id = section["section_id"]
        provision = LEGAL[f"{document.id}_Section{section_id}"]
        if (act, LEGAL.hasProvision, provision) not in kg.graph:
            problems.append(f"section {section_id} is not linked to its Act")
        if (provision, RDF.type, LEGAL.Provision) not in kg.graph:
            problems.append(f"section {section_id} provision individual is missing")

        number = kg.graph.value(provision, LEGAL.sectionNumber)
        if number is None or str(number) != section_id:
            problems.append(f"section {section_id} has a mismatched RDF sectionNumber")
        title = kg.graph.value(provision, LEGAL.sectionTitle)
        if title is None or str(title) != str(section.get("title", "")):
            problems.append(f"section {section_id} has a mismatched RDF title")

        passages = set(kg.graph.objects(provision, LEGAL.containsPassage))
        if len(passages) != 1:
            problems.append(
                f"section {section_id} should have one text passage, got {len(passages)}"
            )
            continue
        passage = next(iter(passages))
        if (passage, RDF.type, LEGAL.TextPassage) not in kg.graph:
            problems.append(f"section {section_id} passage individual is missing")
        text = kg.graph.value(passage, LEGAL.text)
        if text is None or str(text) != str(section.get("text", "")):
            problems.append(f"section {section_id} has mismatched passage text")
        page = kg.graph.value(passage, LEGAL.pageNumber)
        if page is None or int(page) != int(section.get("start_page", 0)):
            problems.append(f"section {section_id} has mismatched passage page")

    return problems


def main() -> None:
    documents = load_documents()
    kg = KnowledgeGraph(config.GENERATED_ONTOLOGY_PATH)
    problems = []
    total_sections = 0

    for document in documents:
        parsed_path = config.PARSED_DIR / f"{document.id}.json"
        if not parsed_path.is_file():
            current = [f"parsed data file is missing: {parsed_path}"]
            section_count = 0
        else:
            try:
                sections = json.loads(parsed_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                sections = []
                current = [f"parsed data is invalid JSON: {exc}"]
            else:
                if not isinstance(sections, list):
                    sections = []
                    current = ["parsed data must be a JSON array"]
                else:
                    current = validate_document(document, sections, kg)
            section_count = len(sections)

        total_sections += section_count
        status = "INVALID" if current else "VALID"
        print(
            f"{document.id}: {section_count}/{document.expected_sections} "
            f"sections — {status}"
        )
        for message in current:
            problems.append(f"{document.id}: {message}")
            print(f"  - {message}")

    print(f"Documents validated: {len(documents)}")
    print(f"Parsed sections: {total_sections}")
    print(
        "RDF totals: "
        f"{len(set(kg.graph.subjects(RDF.type, LEGAL.Provision)))} provisions, "
        f"{len(set(kg.graph.subjects(RDF.type, LEGAL.TextPassage)))} passages, "
        f"{len(set(kg.graph.subjects(RDF.type, LEGAL.ReferenceMention)))} references"
    )
    if problems:
        raise SystemExit(1)
    print("VALID")
