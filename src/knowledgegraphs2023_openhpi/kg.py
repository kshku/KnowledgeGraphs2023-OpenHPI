import re
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from . import config
from .sparql import run_ask, run_select

LEGAL = Namespace(f"{config.ONTOLOGY_IRI}#")
QUERY_PREFIXES = (
    f"PREFIX legal: <{config.ONTOLOGY_IRI}#>\n"
    "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n"
    "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
    "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n"
)
SECTION_ID_PATTERN = re.compile(r"(?P<number>\d+)(?P<suffix>-?[A-Za-z]*)")


def _reference_index(mention: URIRef) -> int:
    match = re.search(r"Reference(\d+)$", str(mention))
    return int(match.group(1)) if match else 0


def _local_name(term) -> str:
    if term is None:
        return ""

    return str(term).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _section_sort_key(section_id: str) -> tuple[int, str, str]:
    match = SECTION_ID_PATTERN.fullmatch(section_id)
    if match is None:
        return (0, section_id.casefold(), section_id)

    suffix = match.group("suffix").replace("-", "").upper()
    return (int(match.group("number")), suffix, section_id)


class KnowledgeGraph:
    """Read-only facade over the generated RDF graph."""

    def __init__(
        self, path: Path, schema_path: Path | None = None
    ):
        self.graph = Graph()
        self.graph.parse(str(path), format="xml")

        self.schema = Graph()
        self.schema_loaded = False

        schema_path = schema_path or config.ONTOLOGY_SCHEMA_PATH

        if Path(schema_path).is_file():
            self.schema.parse(str(schema_path), format="xml")
            self.schema_loaded = True

    def _act(self, document_id: str) -> URIRef:
        return LEGAL[document_id]

    def _documents(self) -> list[dict]:
        return self.list_documents()

    def _resolve_document_id(self, document_id: str | None) -> str:
        if document_id is not None:
            exists = run_ask(
                self.graph,
                QUERY_PREFIXES
                + "ASK { ?act a legal:Act . FILTER(?act = ?document) }",
                {"document": self._act(document_id)},
            )
            if not exists:
                raise ValueError(f"Unknown document ID: {document_id}")
            return document_id

        documents = self.list_documents()
        if len(documents) == 1:
            return documents[0]["document_id"]
        if not documents:
            raise ValueError("The knowledge graph has no legal documents")
        raise ValueError(
            "document_id is required when multiple documents are loaded"
        )

    def _provision(self, document_id: str, section_id: str) -> URIRef:
        return LEGAL[f"{document_id}_Section{section_id}"]

    def _namespace(self) -> str:
        return f"{config.ONTOLOGY_IRI}#"

    def get_schema(self) -> dict:
        """Describe the ontology and the size of the instance graph."""

        def properties(property_type) -> list[dict]:
            rows = run_select(
                self.schema,
                QUERY_PREFIXES
                + "SELECT DISTINCT ?property ?domain ?range WHERE { "
                "?property a ?property_type . "
                "OPTIONAL { ?property rdfs:domain ?domain } "
                "OPTIONAL { ?property rdfs:range ?range } "
                "} ORDER BY ?property",
                {"property_type": property_type},
            )
            return [
                {
                    "name": _local_name(row["property"]),
                    "domain": _local_name(row.get("domain")),
                    "range": _local_name(row.get("range")),
                }
                for row in rows
            ]

        classes = run_select(
            self.schema,
            QUERY_PREFIXES
            + "SELECT DISTINCT ?class WHERE { ?class a owl:Class } "
            "ORDER BY ?class",
        )
        subclasses = run_select(
            self.schema,
            QUERY_PREFIXES
            + "SELECT DISTINCT ?class ?parent WHERE { "
            "?class a owl:Class ; rdfs:subClassOf ?parent . "
            "} ORDER BY ?class ?parent",
        )
        subproperties = run_select(
            self.schema,
            QUERY_PREFIXES
            + "SELECT DISTINCT ?property ?parent WHERE { "
            "VALUES ?kind { owl:ObjectProperty owl:DatatypeProperty } "
            "?property a ?kind ; rdfs:subPropertyOf ?parent . "
            "FILTER(?parent != owl:topObjectProperty && "
            "?parent != owl:topDataProperty) "
            "} ORDER BY ?property ?parent",
        )

        def instance_count(class_uri: URIRef) -> int:
            [row] = run_select(
                self.graph,
                QUERY_PREFIXES
                + "SELECT (COUNT(DISTINCT ?instance) AS ?count) WHERE { "
                "?instance a ?class }",
                {"class": class_uri},
            )
            return int(row["count"] or 0)

        counts = {
            "provisions": instance_count(LEGAL.Provision),
            "text_passages": instance_count(LEGAL.TextPassage),
            "reference_mentions": instance_count(LEGAL.ReferenceMention),
        }

        return {
            "schema_loaded": self.schema_loaded,
            "prefixes": {"legal": self._namespace()},
            "classes": [_local_name(row["class"]) for row in classes],
            "object_properties": properties(OWL.ObjectProperty),
            "datatype_properties": properties(OWL.DatatypeProperty),
            "hierarchy": {
                "subclasses": [
                    {
                        "class": _local_name(row["class"]),
                        "subclass_of": _local_name(row["parent"]),
                    }
                    for row in subclasses
                ],
                "subproperties": [
                    {
                        "property": _local_name(row["property"]),
                        "subproperty_of": _local_name(row["parent"]),
                    }
                    for row in subproperties
                ],
            },
            "counts": counts,
        }

    def list_documents(self) -> list[dict]:
        rows = run_select(
            self.graph,
            QUERY_PREFIXES
            + "SELECT ?act ?title ?source_url "
            "(COUNT(DISTINCT ?provision) AS ?section_count) WHERE { "
            "?act a legal:Act ; legal:title ?title ; "
            "legal:hasProvision ?provision . "
            "OPTIONAL { ?act legal:sourceURL ?source_url } "
            "} GROUP BY ?act ?title ?source_url ORDER BY ?act",
        )
        return [
            {
                "document_id": _local_name(row["act"]),
                "title": row["title"] or "",
                "source_url": row.get("source_url"),
                "section_count": int(row["section_count"] or 0),
            }
            for row in rows
        ]

    def section_exists(
        self, section_id: str, document_id: str | None = None
    ) -> bool:
        resolved_id = self._resolve_document_id(document_id)
        return run_ask(
            self.graph,
            QUERY_PREFIXES
            + "ASK { ?act a legal:Act ; legal:hasProvision ?provision . "
            "?provision a legal:Provision ; legal:sectionNumber ?section_id . "
            "FILTER(?act = ?document && ?section_id = ?requested_section) }",
            {
                "document": self._act(resolved_id),
                "requested_section": Literal(section_id),
            },
        )

    def list_sections(self, document_id: str | None = None) -> list[dict]:
        filter_document = ""
        bindings = {}
        if document_id is not None:
            resolved_id = self._resolve_document_id(document_id)
            filter_document = "FILTER(?act = ?requested_document) "
            bindings["requested_document"] = self._act(resolved_id)

        rows = run_select(
            self.graph,
            QUERY_PREFIXES
            + "SELECT ?act ?document_title ?source_url ?section_id ?title "
            "(xsd:integer(REPLACE(STR(?section_id), "
            "\"^([0-9]+).*$\", \"$1\")) AS ?section_order) "
            "(UCASE(REPLACE(STR(?section_id), \"^[0-9]+\", \"\")) "
            "AS ?section_suffix) WHERE { "
            "?act a legal:Act ; legal:title ?document_title ; "
            "legal:hasProvision ?provision . "
            "?provision a legal:Provision ; legal:sectionNumber ?section_id ; "
            "legal:sectionTitle ?title . "
            "OPTIONAL { ?act legal:sourceURL ?source_url } "
            f"{filter_document}"
            "} ORDER BY STR(?act) ?section_order ?section_suffix",
            bindings,
        )
        return [
            {
                "document_id": _local_name(row["act"]),
                "document_title": row["document_title"] or "",
                "source_url": row.get("source_url"),
                "section_id": row["section_id"],
                "title": row["title"] or "",
            }
            for row in rows
        ]

    def get_section(
        self, section_id: str, document_id: str | None = None
    ) -> dict | None:
        resolved_id = self._resolve_document_id(document_id)
        if not self.section_exists(section_id, resolved_id):
            return None

        document = next(
            item
            for item in self._documents()
            if item["document_id"] == resolved_id
        )
        provision = self._provision(resolved_id, section_id)
        passage = self.graph.value(provision, LEGAL.containsPassage)
        text = self.graph.value(passage, LEGAL.text) if passage else None
        page = self.graph.value(passage, LEGAL.pageNumber) if passage else None
        title = self.graph.value(provision, LEGAL.sectionTitle)

        return {
            "document_id": document["document_id"],
            "document_title": document["title"],
            "source_url": document["source_url"],
            "section_id": section_id,
            "title": str(title or ""),
            "text": str(text or ""),
            "start_page": int(page) if page is not None else None,
            "references": self.get_references(section_id, resolved_id),
            "referenced_by": self.get_referenced_by(section_id, resolved_id),
        }

    def get_references(
        self, section_id: str, document_id: str | None = None
    ) -> list[dict]:
        resolved_id = self._resolve_document_id(document_id)
        if not self.section_exists(section_id, resolved_id):
            return []

        provision = self._provision(resolved_id, section_id)
        passage = self.graph.value(provision, LEGAL.containsPassage)
        if passage is None:
            return []

        mentions = sorted(
            self.graph.subjects(LEGAL.occursIn, passage),
            key=_reference_index,
        )
        references = []

        for mention in mentions:
            target = self.graph.value(mention, LEGAL.referencesProvision)
            target_id = None
            if target is not None:
                value = self.graph.value(target, LEGAL.sectionNumber)
                if value is not None:
                    target_id = str(value)

            external_law = self.graph.value(mention, LEGAL.externalLaw)
            references.append(
                {
                    "reference_text": str(
                        self.graph.value(mention, LEGAL.referenceText) or ""
                    ),
                    "status": str(
                        self.graph.value(mention, LEGAL.resolutionStatus) or ""
                    ),
                    "target": target_id,
                    "external_law": (
                        str(external_law)
                        if external_law is not None
                        else None
                    ),
                }
            )

        return references

    def get_referenced_by(
        self, section_id: str, document_id: str | None = None
    ) -> list[str]:
        resolved_id = self._resolve_document_id(document_id)
        if not self.section_exists(section_id, resolved_id):
            return []

        target = self._provision(resolved_id, section_id)
        act = self._act(resolved_id)
        sources = set()

        for mention in self.graph.subjects(LEGAL.referencesProvision, target):
            passage = self.graph.value(mention, LEGAL.occursIn)
            if passage is None:
                continue

            for provision in self.graph.subjects(LEGAL.containsPassage, passage):
                if (act, LEGAL.hasProvision, provision) not in self.graph:
                    continue
                source_id = self.graph.value(provision, LEGAL.sectionNumber)
                if source_id is not None:
                    sources.add(str(source_id))

        return sorted(sources, key=_section_sort_key)

    def get_external_references(
        self, section_id: str, document_id: str | None = None
    ) -> list[str]:
        return [
            reference["external_law"]
            for reference in self.get_references(section_id, document_id)
            if reference["external_law"]
        ]

    def find_sections(
        self, query: str, document_id: str | None = None
    ) -> list[dict]:
        needle = query.strip().lower()
        if not needle:
            return []

        matches = []
        for section in self.list_sections(document_id):
            data = self.get_section(section["section_id"], section["document_id"])
            if data is None:
                continue

            combined = f"{data['title']}\n{data['text']}"
            index = combined.lower().find(needle)
            if index == -1:
                continue

            start = max(0, index - 60)
            end = min(len(combined), index + len(needle) + 140)
            snippet = re.sub(r"\s+", " ", combined[start:end]).strip()
            matches.append(
                {
                    "document_id": data["document_id"],
                    "document_title": data["document_title"],
                    "source_url": data["source_url"],
                    "section_id": data["section_id"],
                    "title": data["title"],
                    "snippet": snippet,
                }
            )

        return matches
