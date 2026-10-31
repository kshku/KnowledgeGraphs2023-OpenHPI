# KnowledgeGraphs2023-OpenHPI

A document-aware legal knowledge graph and LangChain agent for Indian Acts.
The ontology is general-purpose; the documents and provisions are instances
loaded from the manifest.

## Ontology

The schema is `ontology/legal-ontology.rdf` (RDF/XML, viewable in Protégé). It
models `LegalDocument`, `Act`, `Provision`, `TextPassage`, and `ReferenceMention`
with relations such as `hasProvision`, `containsPassage`, and
`referencesProvision`. The `sectionNumber` property is a string, so section IDs
such as `2A`, `4-I`, and `53-O` are preserved.

The combined generated graph is `ontology/generated/legal-documents.rdf`. Open
the schema and generated graph together in Protégé to inspect the ontology and
its individuals, or load either RDF/XML file with RDFLib.

The manifest at `data/documents.json` currently registers:

| Document | PDF | Provisions |
|---|---|---:|
| The Railways Act, 1989 | `A1989-24.pdf` | 234 |
| The Multimodal Transportation of Goods Act, 1993 | `a1993-28.pdf` | 33 |
| The Competition Act, 2002 | `A2003-12.pdf` | 97 |
| The Food Safety and Standards Act, 2006 | `A2006-34.pdf` | 101 |
| The Legal Metrology Act, 2009 | `a2010-1.pdf` | 57 |
| The Bureau of Indian Standards Act, 2016 | `A2016-11.pdf` | 43 |
| The Consumer Protection Act, 2019 | `A2019-35.pdf` | 107 |
| The Jammu and Kashmir Reorganisation Act, 2019 | `a2019-34.pdf` | 107 |
| The Mediation Act, 2023 | `a2023-32.pdf` | 65 |

## Data extraction and rebuilding

The reproducible pipeline is:

```text
PDF -> page-text JSONL -> parsed section JSON -> combined RDF/XML
```

`extract` processes every manifest PDF. It can also process one document by ID;
the old PDF-path form remains available for PDFs already registered in the
manifest.

```bash
# Extract and parse all manifest documents
uv run python -m knowledgegraphs2023_openhpi extract

# Or just one document
uv run python -m knowledgegraphs2023_openhpi extract \
  --document competition-act-2002

# Combine all parsed documents into one RDF graph
uv run python -m knowledgegraphs2023_openhpi build

# Check parsed data and document-scoped RDF links/counts
uv run python scripts/validate.py
uv run pytest -q
```

Page text is written to `data/extracted/<document-id>.jsonl` (one JSON record per
page). Parsed provisions are JSON arrays at `data/parsed/<document-id>.json`.
The generator combines these into `ontology/generated/legal-documents.rdf`.
The validator checks each Act independently, including section IDs, passages,
and document-to-provision links.

### Adding another Act

1. Download a text-extractable PDF and save it under `data/`.
2. Add an entry to `data/documents.json` with a stable lowercase hyphenated `id`,
   `title`, project-relative `pdf` path, `expected_sections` count, and
   `source_url` if available.
3. If its heading layout differs from the supported IndiaCode formats, add
   parser hints (`first_section_pattern`, `section_pattern`, or `end_marker`) to
   that entry.
4. Run `extract`, `build`, and `scripts/validate.py` as shown above.

For example, a manifest entry looks like:

```json
{
  "id": "example-act-2025",
  "title": "The Example Act, 2025",
  "pdf": "data/example-act-2025.pdf",
  "source_url": "",
  "expected_sections": 42
}
```

The graph retains each document's own section IDs, so equal IDs in different
Acts do not collide. Reference resolution is within the source Act; cross-Act
linking is not currently performed.

## Querying the graph

Section queries require a document ID when more than one Act is loaded.
`find` can search all documents or be filtered to one Act:

```bash
uv run python -m knowledgegraphs2023_openhpi query \
  --document consumer-protection-act-2019 --section 2
uv run python -m knowledgegraphs2023_openhpi query \
  --document competition-act-2002 --section 53-O
uv run python -m knowledgegraphs2023_openhpi find "refund"
uv run python -m knowledgegraphs2023_openhpi find "competition" \
  --document competition-act-2002
```

## Agent

The agent in `src/knowledgegraphs2023_openhpi/agent/` uses typed traversal tools
including `kg_list_documents`, `kg_list_sections`, `kg_get_section`,
`kg_find_sections`, and reference tools, plus read-only `kg_sparql`. It discovers
Act IDs, scopes section queries to the right Act, grounds answers in graph
results, and cites the Act title and section ID (plus source URL when present).
Before SPARQL, it calls `kg_get_schema` to learn the available ontology terms.

Set up the model in `.env` (see `.env.example`), then run:

```bash
uv sync --extra openai
uv run python -m knowledgegraphs2023_openhpi ask \
  "What are the rights of a consumer under the Consumer Protection Act?"
uv run python -m knowledgegraphs2023_openhpi chat
```

`KG_MODEL_PROVIDER` and `KG_MODEL_NAME` select the model. Provider extras are
`openai`, `ollama`, `gemini`, `anthropic`, and `openrouter`.
