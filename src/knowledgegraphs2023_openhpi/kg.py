import re
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from . import config

LEGAL = Namespace(f"{config.ONTOLOGY_IRI}#")


def _reference_index(mention: URIRef) -> int:
    match = re.search(r"Reference(\d+)$", str(mention))
    return int(match.group(1)) if match else 0


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

        if schema_path is not None:
            self.schema.parse(str(schema_path), format="xml")

    def _provision(self, number: int) -> URIRef:
        return LEGAL[f"CPA2019_Section{number}"]

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
            "prefixes": {"legal": f"{config.ONTOLOGY_IRI}#"},
            "classes": sorted(
                _local_name(term)
                for term in self.schema.subjects(RDF.type, OWL.Class)
            ),
            "object_properties": properties(OWL.ObjectProperty),
            "datatype_properties": properties(OWL.DatatypeProperty),
            "counts": counts,
        }

    def section_exists(self, number: int) -> bool:
        return (
            self._provision(number),
            RDF.type,
            LEGAL.Provision,
        ) in self.graph

    def list_sections(self) -> list[dict]:
        sections = []

        for provision in self.graph.subjects(RDF.type, LEGAL.Provision):
            number = self.graph.value(provision, LEGAL.sectionNumber)
            if number is None:
                continue

            title = self.graph.value(provision, LEGAL.sectionTitle)
            sections.append(
                {"number": int(number), "title": str(title or "")}
            )

        return sorted(sections, key=lambda section: section["number"])

    def get_section(self, number: int) -> dict | None:
        if not self.section_exists(number):
            return None

        provision = self._provision(number)
        passage = self.graph.value(provision, LEGAL.containsPassage)

        text = (
            self.graph.value(passage, LEGAL.text) if passage else None
        )
        page = (
            self.graph.value(passage, LEGAL.pageNumber)
            if passage
            else None
        )
        title = self.graph.value(provision, LEGAL.sectionTitle)

        return {
            "number": number,
            "title": str(title or ""),
            "text": str(text or ""),
            "start_page": int(page) if page is not None else None,
            "references": self.get_references(number),
            "referenced_by": self.get_referenced_by(number),
        }

    def get_references(self, number: int) -> list[dict]:
        if not self.section_exists(number):
            return []

        provision = self._provision(number)
        passage = self.graph.value(provision, LEGAL.containsPassage)

        if passage is None:
            return []

        mentions = sorted(
            self.graph.subjects(LEGAL.occursIn, passage),
            key=_reference_index,
        )

        references = []

        for mention in mentions:
            target = self.graph.value(
                mention, LEGAL.referencesProvision
            )
            target_number = None

            if target is not None:
                value = self.graph.value(target, LEGAL.sectionNumber)
                if value is not None:
                    target_number = int(value)

            external_law = self.graph.value(mention, LEGAL.externalLaw)

            references.append(
                {
                    "reference_text": str(
                        self.graph.value(mention, LEGAL.referenceText)
                        or ""
                    ),
                    "status": str(
                        self.graph.value(mention, LEGAL.resolutionStatus)
                        or ""
                    ),
                    "target": target_number,
                    "external_law": (
                        str(external_law)
                        if external_law is not None
                        else None
                    ),
                }
            )

        return references

    def get_referenced_by(self, number: int) -> list[int]:
        if not self.section_exists(number):
            return []

        target = self._provision(number)
        sources = set()

        for mention in self.graph.subjects(
            LEGAL.referencesProvision, target
        ):
            passage = self.graph.value(mention, LEGAL.occursIn)
            if passage is None:
                continue

            provision = self.graph.value(
                None, LEGAL.containsPassage, passage
            )
            if provision is None:
                continue

            source = self.graph.value(
                provision, LEGAL.sectionNumber
            )
            if source is not None:
                sources.add(int(source))

        return sorted(sources)

    def get_external_references(self, number: int) -> list[str]:
        return [
            reference["external_law"]
            for reference in self.get_references(number)
            if reference["external_law"]
        ]

    def find_sections(self, query: str) -> list[dict]:
        needle = query.strip().lower()

        if not needle:
            return []

        matches = []

        for section in self.list_sections():
            data = self.get_section(section["number"])
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
                    "number": data["number"],
                    "title": data["title"],
                    "snippet": snippet,
                }
            )

        return matches
