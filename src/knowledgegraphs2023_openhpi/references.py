import re
from dataclasses import dataclass
from typing import Collection, Iterator


EXTERNAL_LAW_PATTERN = re.compile(
    r"(?:of|under|within\s+the\s+meaning\s+of|as\s+provided\s+by)\s+"
    r"(?:the\s+)?"
    r"(?:First\s+Schedule\s+to\s+)?"
    r"(?P<law>Indian\s+Penal\s+Code"
    r"|General\s+Clauses\s+Act(?:\s*,?\s*\d{4})?"
    r"|Finance\s+Act(?:\s*,?\s*\d{4})?"
    r"|Food\s+Safety\s+and\s+Standards\s+Act(?:\s*,?\s*\d{4})?"
    r"|Code\s+of\s+Criminal\s+Procedure(?:\s*,?\s*\d{4})?"
    r"|Code\s+of\s+Civil\s+Procedure(?:\s*,?\s*\d{4})?"
    r"|Information\s+Technology\s+Act(?:\s*,?\s*\d{4})?"
    r"|Companies\s+Act(?:\s*,?\s*\d{4})?)\b",
    re.IGNORECASE,
)

CITATION_ID = r"\d+(?:-?[A-Za-z]+)?"
CITATION_PATTERN = re.compile(
    rf"\bsections?\s+(?P<first>{CITATION_ID})"
    rf"(?P<tail>(?:\s*(?:,|and|to)\s*{CITATION_ID})*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Reference:
    text: str
    target: str
    is_external: bool = False
    external_law: str | None = None


def _target_ids(first: str, tail: str) -> list[str]:
    """Expand enumerated and purely numeric section ranges into section IDs."""
    targets = [first]
    previous = None

    tokens = re.findall(rf"{CITATION_ID}|to|and|,", tail, re.IGNORECASE)

    for token in tokens:
        lowered = token.lower()

        if lowered in {"to", "and", ","}:
            previous = lowered
            continue

        if previous == "to" and targets[-1].isdigit() and token.isdigit():
            start = int(targets[-1])
            end = int(token)
            if end > start:
                targets.extend(str(number) for number in range(start + 1, end + 1))
            else:
                targets.append(token)
        else:
            targets.append(token)

        previous = None

    return targets


def extract_references(text: str) -> Iterator[Reference]:
    """Yield references found in a provision's text."""
    for match in CITATION_PATTERN.finditer(text):
        reference_text = match.group(0)

        # Classify only on the text between this citation and the next one,
        # so a law mentioned for a later reference does not leak backwards.
        following_text = text[match.end() :]
        next_citation = CITATION_PATTERN.search(following_text)

        if next_citation is not None:
            following_text = following_text[: next_citation.start()]

        external_match = EXTERNAL_LAW_PATTERN.search(
            following_text[:200]
        )
        external_law = (
            re.sub(r"\s+", " ", external_match.group("law")).strip()
            if external_match
            else None
        )

        for section_id in _target_ids(
            match.group("first"), match.group("tail")
        ):
            yield Reference(
                text=reference_text,
                target=section_id,
                is_external=external_match is not None,
                external_law=external_law,
            )


def resolution_status(
    reference: Reference, section_ids: Collection[str]
) -> str:
    """Return "external", "resolved", or "unresolved"."""
    if reference.is_external:
        return "external"

    if reference.target in section_ids:
        return "resolved"

    return "unresolved"
