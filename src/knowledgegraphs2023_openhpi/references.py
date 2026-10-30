import re
from dataclasses import dataclass
from typing import Iterator


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

CITATION_PATTERN = re.compile(
    r"\bsections?\s+(\d+)"
    r"((?:\s*(?:,|and|to)\s*\d+)*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Reference:
    text: str
    target: int
    is_external: bool = False
    external_law: str | None = None


def _target_numbers(first: int, tail: str) -> list[int]:
    """Expand "2, 3 and 4" and "2 to 5" into individual section numbers."""
    numbers = [first]
    previous = None

    for token in re.findall(r"\d+|to|and|,", tail, re.IGNORECASE):
        lowered = token.lower()

        if token.isdigit():
            number = int(token)

            if previous == "to":
                numbers.extend(range(numbers[-1] + 1, number + 1))
            else:
                numbers.append(number)

        previous = lowered

    return numbers


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

        for number in _target_numbers(
            int(match.group(1)), match.group(2)
        ):
            yield Reference(
                text=reference_text,
                target=number,
                is_external=external_match is not None,
                external_law=external_law,
            )


def resolution_status(
    reference: Reference, max_section: int = 107
) -> str:
    """Return "external", "resolved", or "unresolved"."""
    if reference.is_external:
        return "external"

    if 1 <= reference.target <= max_section:
        return "resolved"

    return "unresolved"
