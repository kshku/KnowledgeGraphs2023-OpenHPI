# KnowledgeGraphs2023-OpenHPI

Knowledge graph and agent for **The Consumer Protection Act, 2019**.

## Ontology

The ontology is in `ontology/legal-ontology.rdf` (Protégé/RDF-XML). It models:

- `LegalDocument`, `Act`, `Provision`, `TextPassage`, `ReferenceMention`
- `hasProvision`, `containsPassage`, `referencesProvision`, `occursIn`
- data properties such as `sectionNumber`, `sectionTitle`, `text`,
  `referenceText`, `resolutionStatus`, `externalLaw`

The generated individuals are in
`ontology/generated/consumer-protection-individuals.rdf`. They are built from
`data/parsed/A2019-35.jsonl` and contain 107 sections, their passages, and the
references between them.

To view the ontology, open either RDF file in Protégé, or load it with RDFLib.
You can also inspect it through the command line:

```bash
uv run python -m knowledgegraphs2023_openhpi query --section 2
uv run python -m knowledgegraphs2023_openhpi find "refund"
```

## Agent

The agent (`src/knowledgegraphs2023_openhpi/agent/`) uses LangChain tools over
the knowledge graph. It has typed traversal tools (`kg_list_sections`,
`kg_get_section`, `kg_find_sections`, `kg_get_references`,
`kg_get_referenced_by`) and a read-only `kg_sparql` tool. Answers are grounded
in tool results and cite section numbers.

Set up the model in `.env` (see `.env.example`), then run:

```bash
uv sync --extra openai

# one question
uv run python -m knowledgegraphs2023_openhpi ask "What are the rights of a consumer?"

# interactive session
uv run python -m knowledgegraphs2023_openhpi chat
```

`KG_MODEL_PROVIDER` and `KG_MODEL_NAME` select the model. Provider extras are
`openai`, `ollama`, `gemini`, `anthropic`, and `openrouter`.

## Build and validate

```bash
# PDF -> data/extracted + data/parsed
uv run python -m knowledgegraphs2023_openhpi extract data/A2019-35.pdf

# parsed sections -> RDF
uv run python -m knowledgegraphs2023_openhpi build

# checks
uv run python scripts/validate.py
uv run pytest
```
