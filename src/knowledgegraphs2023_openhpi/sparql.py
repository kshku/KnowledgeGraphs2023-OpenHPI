import re

from rdflib import Graph

READ_FORMS = ("SELECT", "ASK", "CONSTRUCT", "DESCRIBE")

FORBIDDEN_KEYWORDS = (
    "INSERT",
    "DELETE",
    "LOAD",
    "CLEAR",
    "DROP",
    "CREATE",
    "ADD",
    "MOVE",
    "COPY",
    "WITH",
)


def validate_read_only(query: str) -> None:
    """Reject anything that is not a read-only SPARQL query."""
    if not query or not query.strip():
        raise ValueError("Empty SPARQL query")

    upper = query.upper()

    if not any(
        re.search(rf"\b{form}\b", upper) for form in READ_FORMS
    ):
        raise ValueError(
            "Only SELECT, ASK, CONSTRUCT or DESCRIBE queries are allowed"
        )

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper):
            raise ValueError(
                f"{keyword} is not allowed: the knowledge graph is read-only"
            )


def _term(value) -> str | None:
    return None if value is None else str(value)


def run_query(
    graph: Graph, query: str, limit: int = 50
) -> dict:
    """Run a read-only query and return JSON-friendly results."""
    validate_read_only(query)

    result = graph.query(query)

    if result.type == "ASK":
        return {"ask": bool(result.askAnswer)}

    if result.type in ("CONSTRUCT", "DESCRIBE"):
        triples = [
            {
                "subject": str(subject),
                "predicate": str(predicate),
                "object": str(obj),
            }
            for subject, predicate, obj in result
        ]
        return {"triples": triples[:limit], "count": len(triples)}

    columns = [str(variable) for variable in result.vars]
    rows = []

    for row in result:
        if len(rows) >= limit:
            break

        rows.append(
            {
                str(variable): _term(row[variable])
                for variable in result.vars
            }
        )

    return {"columns": columns, "rows": rows}
