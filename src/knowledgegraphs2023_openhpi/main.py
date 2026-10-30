import argparse
import json
from pathlib import Path

import pymupdf

from . import config
from .kg import KnowledgeGraph
from .ontology_generator import generate_ontology
from .parser import parse
from .pdf_utils import extract_pdf

PARSED_INPUT = config.PARSED_DIR / "A2019-35.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="knowledgegraphs2023-openhpi",
        description="Consumer Protection Act knowledge graph and agent",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser(
        "extract", help="Extract and parse a PDF into sections"
    )
    extract.add_argument("pdf", type=Path)

    subparsers.add_parser(
        "build", help="Generate the RDF ontology from parsed sections"
    )

    query = subparsers.add_parser(
        "query", help="Show one section from the knowledge graph"
    )
    query.add_argument("--section", type=int, required=True)

    find = subparsers.add_parser(
        "find", help="Find sections by title or text"
    )
    find.add_argument("query")

    ask = subparsers.add_parser(
        "ask", help="Ask the agent one question"
    )
    ask.add_argument("question")

    subparsers.add_parser(
        "chat", help="Start an interactive agent session"
    )

    return parser


def _load_kg() -> KnowledgeGraph:
    if not config.GENERATED_ONTOLOGY_PATH.is_file():
        raise FileNotFoundError(
            "Generated ontology not found: "
            f"{config.GENERATED_ONTOLOGY_PATH}. Run `build` first."
        )

    return KnowledgeGraph(
        config.GENERATED_ONTOLOGY_PATH, config.ONTOLOGY_SCHEMA_PATH
    )


def command_extract(pdf_path: Path) -> None:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    extracted_path = config.EXTRACTED_DIR / f"{pdf_path.stem}.jsonl"
    parsed_path = config.PARSED_DIR / f"{pdf_path.stem}.jsonl"

    config.EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    config.PARSED_DIR.mkdir(parents=True, exist_ok=True)

    extract_pdf(pdf_path, extracted_path)
    parse(extracted_path, parsed_path)


def command_build(input_path: Path = PARSED_INPUT) -> None:
    with input_path.open(encoding="utf-8") as file:
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


def command_query(section_number: int) -> None:
    section = _load_kg().get_section(section_number)

    if section is None:
        raise ValueError(f"Section {section_number} not found")

    print(json.dumps(section, indent=2, ensure_ascii=False))


def command_find(query: str) -> None:
    print(
        json.dumps(
            _load_kg().find_sections(query),
            indent=2,
            ensure_ascii=False,
        )
    )


def command_ask(question: str) -> None:
    from .agent import build_agent

    kg = _load_kg()
    agent = build_agent(kg, kg.graph)

    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]}
    )

    print(result["messages"][-1].content)


def command_chat() -> None:
    from .agent import build_agent

    kg = _load_kg()
    agent = build_agent(kg, kg.graph)

    while True:
        try:
            question = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if question.strip().lower() in {"exit", "quit"}:
            break

        if not question.strip():
            continue

        print()

        for chunk, _metadata in agent.stream(
            {"messages": [{"role": "user", "content": question}]},
            stream_mode="messages",
        ):
            content = getattr(chunk, "content", "")
            if content:
                print(content, end="", flush=True)

        print("\n")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        match args.command:
            case "extract":
                command_extract(args.pdf)
            case "build":
                command_build()
            case "query":
                command_query(args.section)
            case "find":
                command_find(args.query)
            case "ask":
                command_ask(args.question)
            case "chat":
                command_chat()
    except (FileNotFoundError, ValueError, pymupdf.FileDataError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
