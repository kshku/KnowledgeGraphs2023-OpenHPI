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
def _local_name(term) -> str:
    if term is None:
        return ""

    return str(term).rsplit("#", 1)[-1].rsplit("/", 1)[-1]

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
        rows = run_select(
            self.graph,
            QUERY_PREFIXES
            + "SELECT ?act ?document_title ?source_url ?section_id ?title "
            "?text ?page WHERE { "
            "?act a legal:Act ; legal:title ?document_title ; "
            "legal:hasProvision ?requested_provision . "
            "?requested_provision a legal:Provision ; "
            "legal:sectionNumber ?section_id ; "
            "legal:sectionTitle ?title ; legal:containsPassage ?passage . "
            "?passage a legal:TextPassage ; legal:text ?text . "
            "OPTIONAL { ?act legal:sourceURL ?source_url } "
            "OPTIONAL { ?passage legal:pageNumber ?page } "
            "FILTER(?act = ?document && ?section_id = ?requested_section) "
            "} LIMIT 1",
            {
                "document": self._act(resolved_id),
                "requested_provision": self._provision(resolved_id, section_id),
                "requested_section": Literal(section_id),
            },
        )
        if not rows:
            return None

        row = rows[0]

        return {
            "document_id": _local_name(row["act"]),
            "document_title": row["document_title"] or "",
            "source_url": row.get("source_url"),
            "section_id": row["section_id"],
            "title": row["title"] or "",
            "text": row["text"] or "",
            "start_page": int(row["page"]) if row.get("page") else None,
            "references": self.get_references(section_id, resolved_id),
            "referenced_by": self.get_referenced_by(section_id, resolved_id),
        }

    def get_references(
        self, section_id: str, document_id: str | None = None
    ) -> list[dict]:
        resolved_id = self._resolve_document_id(document_id)
        rows = run_select(
            self.graph,
            QUERY_PREFIXES
            + "SELECT ?reference_text ?status ?target_id ?external_law "
            "(xsd:integer(REPLACE(STR(?mention), "
            "\".*Reference([0-9]+)$\", \"$1\")) AS ?reference_order) "
            "WHERE { "
            "?act a legal:Act ; legal:hasProvision ?source_provision . "
            "?source_provision legal:sectionNumber ?source_id ; "
            "legal:containsPassage ?passage . "
            "?mention a legal:ReferenceMention ; legal:occursIn ?passage ; "
            "legal:referenceText ?reference_text ; "
            "legal:resolutionStatus ?status . "
            "OPTIONAL { ?mention legal:referencesProvision ?target . "
            "?target legal:sectionNumber ?target_id } "
            "OPTIONAL { ?mention legal:externalLaw ?external_law } "
            "FILTER(?act = ?document && ?source_id = ?requested_section) "
            "} ORDER BY ?reference_order",
            {
                "document": self._act(resolved_id),
                "source_provision": self._provision(resolved_id, section_id),
                "requested_section": Literal(section_id),
            },
        )
        return [
            {
                "reference_text": row["reference_text"] or "",
                "status": row["status"] or "",
                "target": row.get("target_id"),
                "external_law": row.get("external_law"),
            }
            for row in rows
        ]

    def get_referenced_by(
        self, section_id: str, document_id: str | None = None
    ) -> list[str]:
        resolved_id = self._resolve_document_id(document_id)
        rows = run_select(
            self.graph,
            QUERY_PREFIXES
            + "SELECT DISTINCT ?source_id "
            "(xsd:integer(REPLACE(STR(?source_id), "
            "\"^([0-9]+).*$\", \"$1\")) AS ?section_order) "
            "(UCASE(REPLACE(STR(?source_id), \"^[0-9]+\", \"\")) "
            "AS ?section_suffix) WHERE { "
            "?act a legal:Act ; legal:hasProvision ?target_provision ; "
            "legal:hasProvision ?source . "
            "?target_provision legal:sectionNumber ?target_id . "
            "?source legal:sectionNumber ?source_id ; "
            "legal:containsPassage ?passage . "
            "?mention a legal:ReferenceMention ; legal:occursIn ?passage ; "
            "legal:referencesProvision ?target_provision . "
            "FILTER(?act = ?document && ?target_id = ?requested_section) "
            "} ORDER BY ?section_order ?section_suffix",
            {
                "document": self._act(resolved_id),
                "target_provision": self._provision(resolved_id, section_id),
                "requested_section": Literal(section_id),
            },
        )
        return [row["source_id"] for row in rows]

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
        needle = query.strip()
        if not needle:
            return []

        document_filter = ""
        bindings = {"needle": Literal(needle)}
        if document_id is not None:
            resolved_id = self._resolve_document_id(document_id)
            document_filter = "FILTER(?document = ?requested_document) "
            bindings["requested_document"] = self._act(resolved_id)

        direct_rows = run_select(
            self.graph,
            QUERY_PREFIXES
            + "SELECT DISTINCT ?document ?document_title ?source_url "
            "?section_id ?title ?text "
            "(xsd:integer(REPLACE(STR(?section_id), "
            "\"^([0-9]+).*$\", \"$1\")) AS ?section_order) "
            "(UCASE(REPLACE(STR(?section_id), \"^[0-9]+\", \"\")) "
            "AS ?section_suffix) WHERE { "
            "?document a legal:Act ; legal:title ?document_title ; "
            "legal:hasProvision ?provision . "
            "?provision a legal:Provision ; legal:sectionNumber ?section_id ; "
            "legal:sectionTitle ?title ; legal:containsPassage ?passage . "
            "?passage a legal:TextPassage ; legal:text ?text . "
            "OPTIONAL { ?document legal:sourceURL ?source_url } "
            f"{document_filter}"
            "FILTER(CONTAINS(LCASE(STR(?section_id)), LCASE(STR(?needle))) || "
            "CONTAINS(LCASE(STR(?title)), LCASE(STR(?needle))) || "
            "CONTAINS(LCASE(STR(?text)), LCASE(STR(?needle)))) "
            "} ORDER BY STR(?document) ?section_order ?section_suffix",
            bindings,
        )

        related_rows = run_select(
            self.graph,
            QUERY_PREFIXES
            + "SELECT DISTINCT ?document ?document_title ?source_url "
            "?section_id ?title ?text ?related_via "
            "(xsd:integer(REPLACE(STR(?section_id), "
            "\"^([0-9]+).*$\", \"$1\")) AS ?section_order) "
            "(UCASE(REPLACE(STR(?section_id), \"^[0-9]+\", \"\")) "
            "AS ?section_suffix) "
            "(IF(?related_via = \"references\", 0, 1) AS ?relation_order) "
            "WHERE { "
            "?document a legal:Act ; legal:title ?document_title ; "
            "legal:hasProvision ?matched . "
            "OPTIONAL { ?document legal:sourceURL ?source_url } "
            "?matched a legal:Provision ; legal:sectionNumber ?matched_id ; "
            "legal:sectionTitle ?matched_title ; legal:containsPassage ?matched_passage . "
            "?matched_passage legal:text ?matched_text . "
            "FILTER(CONTAINS(LCASE(STR(?matched_id)), LCASE(STR(?needle))) || "
            "CONTAINS(LCASE(STR(?matched_title)), LCASE(STR(?needle))) || "
            "CONTAINS(LCASE(STR(?matched_text)), LCASE(STR(?needle)))) "
            f"{document_filter}"
            "{ "
            "?mention a legal:ReferenceMention ; legal:occursIn ?matched_passage ; "
            "legal:referencesProvision ?related . "
            "BIND(\"references\" AS ?related_via) "
            "} UNION { "
            "?mention a legal:ReferenceMention ; legal:referencesProvision ?matched ; "
            "legal:occursIn ?related_passage . "
            "?related legal:containsPassage ?related_passage . "
            "BIND(\"referenced_by\" AS ?related_via) "
            "} "
            "?document legal:hasProvision ?related . "
            "?related a legal:Provision ; legal:sectionNumber ?section_id ; "
            "legal:sectionTitle ?title ; legal:containsPassage ?passage . "
            "?passage legal:text ?text . "
            "FILTER(?related != ?matched) "
            "} ORDER BY STR(?document) ?section_order ?section_suffix ?relation_order",
            bindings,
        )

        direct_results = []
        direct_keys = set()
        for row in direct_rows:
            key = (_local_name(row["document"]), row["section_id"])
            direct_keys.add(key)
            direct_results.append(
                self._search_result(row, needle, "direct", None)
            )

        related_results = []
        seen_related = set(direct_keys)
        for row in related_rows:
            key = (_local_name(row["document"]), row["section_id"])
            if key in seen_related:
                continue
            seen_related.add(key)
            related_results.append(
                self._search_result(
                    row, needle, "related", row["related_via"]
                )
            )

        return direct_results + related_results

    @staticmethod
    def _search_result(
        row: dict,
        query: str,
        match_type: str,
        related_via: str | None,
    ) -> dict:
        title = row["title"] or ""
        text = row["text"] or ""
        combined = f"{title}\n{text}"
        index = combined.lower().find(query.lower())
        if match_type == "direct" and index >= 0:
            start = max(0, index - 60)
            end = min(len(combined), index + len(query) + 140)
            snippet = combined[start:end]
        else:
            snippet = f"{title} {text[:200]}"

        return {
            "document_id": _local_name(row["document"]),
            "document_title": row["document_title"] or "",
            "source_url": row.get("source_url"),
            "section_id": row["section_id"],
            "title": title,
            "snippet": re.sub(r"\s+", " ", snippet).strip(),
            "match_type": match_type,
            "related_via": related_via,
        }
