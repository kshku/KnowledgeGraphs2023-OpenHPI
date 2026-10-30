from langchain_core.tools import tool

from ..kg import KnowledgeGraph
from ..settings import settings
from ..sparql import run_query


def build_tools(kg: KnowledgeGraph, graph) -> list:
    """Create the read-only tools the agent can call."""

    @tool
    def kg_list_sections() -> list[dict]:
        """List every section number and title in the Act."""
        return kg.list_sections()

    @tool
    def kg_get_section(section_number: int) -> dict | None:
        """Return a section's title, full text, page, outbound references
        and the sections that reference it. Returns null if it does not exist."""
        return kg.get_section(section_number)

    @tool
    def kg_find_sections(query: str) -> list[dict]:
        """Find sections whose title or text contains the query string
        (case-insensitive). Returns number, title and a short snippet."""
        return kg.find_sections(query)

    @tool
    def kg_get_references(section_number: int) -> list[dict]:
        """List the references made by a section, with resolution status,
        target section, or external law if any."""
        return kg.get_references(section_number)

    @tool
    def kg_get_referenced_by(section_number: int) -> list[int]:
        """List the section numbers that reference the given section."""
        return kg.get_referenced_by(section_number)

    @tool
    def kg_sparql(query: str) -> dict:
        """Run a read-only SPARQL SELECT/ASK/CONSTRUCT/DESCRIBE query against
        the RDF graph and return columns and rows."""
        return run_query(graph, query, settings.max_sparql_rows)

    return [
        kg_list_sections,
        kg_get_section,
        kg_find_sections,
        kg_get_references,
        kg_get_referenced_by,
        kg_sparql,
    ]
