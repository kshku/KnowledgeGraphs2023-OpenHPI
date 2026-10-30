import re
from dataclasses import dataclass
from typing import Iterator


EXTERNAL_LAW_PATTERN = re.compile(
    r"^\s*(?:of|under|within the meaning of|as provided by)\s+"
    r"(?:the\s+)?"
    r"(?:First Schedule\s+to\s+)?"
    r"(?P<law>Indian Penal Code"
    r"|Finance Act(?:\s*,?\s*\d{4})?"
    r"|Food Safety and Standards Act(?:\s*,?\s*\d{4})?"
    r"|Code of Criminal Procedure"
    r"|Code of Civil Procedure"
    r"|Information Technology Act(?:\s*,?\s*\d{4})?"
    r"|Companies Act(?:\s*,?\s*\d{4})?)\b",
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

        # Classify only on the text immediately after the citation so a law
        # mentioned elsewhere in the section does not affect this reference.
        following_text = text[match.end() : match.end() + 120]
        external_match = EXTERNAL_LAW_PATTERN.search(following_text)
        external_law = (
            external_match.group("law") if external_match else None
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
