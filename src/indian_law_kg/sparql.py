import re
from collections.abc import Mapping

from rdflib import Graph
from rdflib.term import Identifier

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
    "SERVICE",
    "FROM",
    "USING",
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


def _execute(
    graph: Graph,
    query: str,
    bindings: Mapping[str, Identifier] | None = None,
):
    validate_read_only(query)
    return graph.query(query, initBindings=bindings or {})


def run_select(
    graph: Graph,
    query: str,
    bindings: Mapping[str, Identifier] | None = None,
) -> list[dict[str, str | None]]:
    """Run a bound read-only SELECT and return JSON-friendly rows."""
    result = _execute(graph, query, bindings)
    if result.type != "SELECT":
        raise ValueError("run_select requires a SPARQL SELECT query")

    return [
        {
            str(variable): _term(row[variable])
            for variable in result.vars
        }
        for row in result
    ]


def run_ask(
    graph: Graph,
    query: str,
    bindings: Mapping[str, Identifier] | None = None,
) -> bool:
    """Run a bound read-only ASK query."""
    result = _execute(graph, query, bindings)
    if result.type != "ASK":
        raise ValueError("run_ask requires a SPARQL ASK query")
    return bool(result.askAnswer)


def run_query(
    graph: Graph, query: str, limit: int = 50
) -> dict:
    """Run a read-only query and return JSON-friendly results."""
    result = _execute(graph, query)

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
