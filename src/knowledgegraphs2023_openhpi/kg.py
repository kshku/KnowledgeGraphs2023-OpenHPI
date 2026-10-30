import re
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from . import config

LEGAL = Namespace(f"{config.ONTOLOGY_IRI}#")
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
        for act in self.graph.subjects(RDF.type, LEGAL.Act):
            if _local_name(act) == document_id:
                return act
        raise ValueError(f"Unknown document ID: {document_id}")

    def _documents(self) -> list[dict]:
        documents = []

        for act in self.graph.subjects(RDF.type, LEGAL.Act):
            document_id = _local_name(act)
            title = self.graph.value(act, LEGAL.title)
            source_url = self.graph.value(act, LEGAL.sourceURL)
            provisions = set(self.graph.objects(act, LEGAL.hasProvision))
            documents.append(
                {
                    "document_id": document_id,
                    "title": str(title or ""),
                    "source_url": str(source_url) if source_url else None,
                    "section_count": len(provisions),
                }
            )

        return sorted(documents, key=lambda item: item["document_id"])

    def _resolve_document_id(self, document_id: str | None) -> str:
        documents = self._documents()
        known_ids = {item["document_id"] for item in documents}

        if document_id is not None:
            if document_id not in known_ids:
                raise ValueError(f"Unknown document ID: {document_id}")
            return document_id

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
        for term in self.schema.subjects(RDF.type, OWL.Class):
            text = str(term)
            separator = "#" if "#" in text else "/"
            return text.rsplit(separator, 1)[0] + separator

        return f"{config.ONTOLOGY_IRI}#"

    def get_schema(self) -> dict:
        """Describe the ontology and the size of the instance graph."""

        def properties(property_type) -> list[dict]:
            items = []

            for prop in self.schema.subjects(RDF.type, property_type):
                items.append(
                    {
                        "name": _local_name(prop),
                        "domain": _local_name(
                            self.schema.value(prop, RDFS.domain)
                        ),
                        "range": _local_name(
                            self.schema.value(prop, RDFS.range)
                        ),
                    }
                )

            return sorted(items, key=lambda item: item["name"])

        subclasses = [
            {
                "class": _local_name(child),
                "subclass_of": _local_name(parent),
            }
            for child in self.schema.subjects(
                RDF.type, OWL.Class
            )
            for parent in self.schema.objects(child, RDFS.subClassOf)
            if isinstance(child, URIRef) and isinstance(parent, URIRef)
        ]

        subproperties = [
            {
                "property": _local_name(prop),
                "subproperty_of": _local_name(parent),
            }
            for prop in set(
                self.schema.subjects(RDF.type, OWL.ObjectProperty)
            )
            | set(
                self.schema.subjects(RDF.type, OWL.DatatypeProperty)
            )
            for parent in self.schema.objects(prop, RDFS.subPropertyOf)
            if isinstance(parent, URIRef)
            and _local_name(parent)
            not in {"topObjectProperty", "topDataProperty"}
        ]

        counts = {
            "provisions": len(
                set(self.graph.subjects(RDF.type, LEGAL.Provision))
            ),
            "text_passages": len(
                set(self.graph.subjects(RDF.type, LEGAL.TextPassage))
            ),
            "reference_mentions": len(
                set(
                    self.graph.subjects(
                        RDF.type, LEGAL.ReferenceMention
                    )
                )
            ),
        }

        return {
            "schema_loaded": self.schema_loaded,
            "prefixes": {"legal": self._namespace()},
            "classes": sorted(
                _local_name(term)
                for term in self.schema.subjects(RDF.type, OWL.Class)
            ),
            "object_properties": properties(OWL.ObjectProperty),
            "datatype_properties": properties(OWL.DatatypeProperty),
            "hierarchy": {
                "subclasses": sorted(
                    subclasses,
                    key=lambda item: (
                        item["class"],
                        item["subclass_of"],
                    ),
                ),
                "subproperties": sorted(
                    subproperties,
                    key=lambda item: (
                        item["property"],
                        item["subproperty_of"],
                    ),
                ),
            },
            "counts": counts,
        }

    def list_documents(self) -> list[dict]:
        return self._documents()

    def section_exists(
        self, section_id: str, document_id: str | None = None
    ) -> bool:
        resolved_id = self._resolve_document_id(document_id)
        return (
            self._provision(resolved_id, section_id),
            RDF.type,
            LEGAL.Provision,
        ) in self.graph

    def list_sections(self, document_id: str | None = None) -> list[dict]:
        documents = self._documents()
        if document_id is not None:
            resolved_id = self._resolve_document_id(document_id)
            documents = [
                item for item in documents if item["document_id"] == resolved_id
            ]

        sections = []
        for document in documents:
            act = self._act(document["document_id"])
            for provision in self.graph.objects(act, LEGAL.hasProvision):
                section_value = self.graph.value(
                    provision, LEGAL.sectionNumber
                )
                if section_value is None:
                    continue

                title = self.graph.value(provision, LEGAL.sectionTitle)
                sections.append(
                    {
                        "document_id": document["document_id"],
                        "document_title": document["title"],
                        "source_url": document["source_url"],
                        "section_id": str(section_value),
                        "title": str(title or ""),
                    }
                )

        return sorted(
            sections,
            key=lambda section: (
                section["document_id"],
                _section_sort_key(section["section_id"]),
            ),
        )

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
