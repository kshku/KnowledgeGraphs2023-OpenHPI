import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

SECTION_START = re.compile(
    r"^\s*(?P<section_id>\d+(?:-?[A-Za-z]+)?)\.\s*(?P<remainder>.*)$"
)
SECTION_SEPARATOR = re.compile(r"\.\s*[—–-]")
CHAPTER_HEADING = re.compile(r"^\s*CHAPTER\s+[IVXLCDM]+\s*$", re.IGNORECASE)
DEFAULT_END_MARKER = re.compile(
    r"^\s*(?:THE\s+)?(?:(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|"
    r"SEVENTH|EIGHTH|NINTH|TENTH|\d+(?:ST|ND|RD|TH)?|[IVXLCDM]+)\s+)?"
    r"SCHEDULES?(?:\s+\[[^\]]*\])?\.?\s*$",
    re.IGNORECASE,
)
FOOTNOTE_START = re.compile(
    r"^(?:Subs\.|Ins\.|Added\.|Omitted\.|Rep\.|The words?\b|Clause\b|"
    r"Cls\.|w\.e\.f\.|vide\b|dated\b|\d{1,2}(?:st|nd|rd|th)\b)",
    re.IGNORECASE,
)


@dataclass
class LegalSection:
    section_id: str
    title: str
    text: str
    start_page: int
    end_page: int


def is_chapter_heading(line: str) -> bool:
    return bool(CHAPTER_HEADING.match(line.strip()))


def _clean_heading_line(line: str) -> str:
    return re.sub(r"^\s*\d+\s*\[", "", line).rstrip()


def _compile_pattern(pattern: str | None, default: re.Pattern) -> re.Pattern:
    compiled = re.compile(pattern) if pattern is not None else default

    if "section_id" not in compiled.groupindex and default is SECTION_START:
        raise ValueError("section_pattern must define a named 'section_id' group")

    return compiled


def _heading_candidate(
    lines: list[tuple[int, str]], index: int, section_pattern: re.Pattern
) -> tuple[str, str] | None:
    cleaned = _clean_heading_line(lines[index][1])
    match = section_pattern.match(cleaned)

    if match is None:
        return None

    section_id = match.group("section_id")
    remainder = match.groupdict().get("remainder") or cleaned[match.end() :]
    if FOOTNOTE_START.match(remainder.strip()):
        return None

    heading = cleaned
    for lookahead in range(1, 5):
        if SECTION_SEPARATOR.search(heading):
            break
        next_index = index + lookahead
        if next_index >= len(lines):
            break

        next_line = _clean_heading_line(lines[next_index][1])
        if section_pattern.match(next_line):
            break
        heading = f"{heading} {next_line.strip()}"

    title_text = heading[match.end("section_id") :]
    title_text = re.sub(r"^\s*[.:]\s*", "", title_text)
    separator = SECTION_SEPARATOR.search(title_text)

    if separator is not None:
        title = title_text[: separator.start()].strip()
        return section_id, title.rstrip(".")

    omitted_title = re.match(
        r"^\s*\[(?P<title>[^\]]+)\]\s*"
        r"\.?\s*(?:[—–-]|Omitted\b|Rep\.|Repealed\b|$)",
        title_text,
        re.IGNORECASE,
    )
    if omitted_title is None:
        return None

    return section_id, omitted_title.group("title").strip().rstrip(".")


def _section_order(section_id: str) -> tuple[int, str]:
    match = re.fullmatch(r"(?P<number>\d+)(?P<suffix>-?[A-Za-z]*)", section_id)
    if match is None:
        raise ValueError(f"Invalid section ID: {section_id}")

    suffix = match.group("suffix").replace("-", "").upper()
    return int(match.group("number")), suffix


def _correct_prefixed_section_id(section_id: str, previous_id: str) -> str:
    """Remove a PDF footnote digit accidentally joined to a suffixed ID."""
    number, separator, suffix = re.fullmatch(
        r"(?P<number>\d+)(?P<separator>-?)(?P<suffix>[A-Za-z]*)", section_id
    ).groups()
    previous_number, _ = _section_order(previous_id)

    if len(number) > len(str(previous_number)) and number[1:] == str(previous_number):
        corrected = f"{number[1:]}{separator}{suffix}"
        if _section_order(corrected) > _section_order(previous_id):
            return corrected

    return section_id


def section_body(lines: list[str]) -> str:
    lines = lines.copy()

    while lines and not lines[-1].strip():
        lines.pop()

    # Remove chapter heading and its following title, if present.
    if lines and lines[-1].strip().isupper() and not is_chapter_heading(lines[-1]):
        if len(lines) >= 2 and is_chapter_heading(lines[-2]):
            lines = lines[:-2]

    return "\n".join(lines).strip()


def parse_sections(
    records: list[dict],
    *,
    first_section_pattern: str | None = None,
    section_pattern: str | None = None,
    end_marker: str | None = None,
) -> list[LegalSection]:
    sections: list[LegalSection] = []
    lines = [
        (record["page"], line)
        for record in records
        for line in record["text"].splitlines()
    ]
    section_start = _compile_pattern(section_pattern, SECTION_START)
    first_section = (
        re.compile(first_section_pattern)
        if first_section_pattern is not None
        else None
    )
    stop_pattern = (
        re.compile(end_marker, re.IGNORECASE)
        if end_marker is not None
        else DEFAULT_END_MARKER
    )

    current_id: str | None = None
    current_title = ""
    current_lines: list[str] = []
    current_start_page = 0
    current_end_page = 0
    seen_ids = set()
    started = False

    for index, (page_number, line) in enumerate(lines):
        normalized = _clean_heading_line(line)

        if started and stop_pattern.match(normalized):
            break

        candidate = _heading_candidate(lines, index, section_start)

        if not started:
            if candidate is None or candidate[0] != "1":
                continue
            if first_section is not None and not first_section.match(normalized):
                continue
            started = True

        if candidate is not None:
            section_id, title = candidate
            if current_id is not None:
                section_id = _correct_prefixed_section_id(
                    section_id, current_id
                )
                if _section_order(section_id) < _section_order(current_id):
                    continue

            if section_id in seen_ids:
                raise ValueError(f"Duplicate section ID: {section_id}")

            if current_id is not None:
                sections.append(
                    LegalSection(
                        section_id=current_id,
                        title=current_title,
                        text=section_body(current_lines),
                        start_page=current_start_page,
                        end_page=current_end_page,
                    )
                )

            seen_ids.add(section_id)
            current_id = section_id
            current_title = title
            current_lines = [line.strip()]
            current_start_page = page_number
            current_end_page = page_number
            continue

        if current_id is not None:
            current_lines.append(line.rstrip())
            current_end_page = page_number

    if current_id is not None:
        sections.append(
            LegalSection(
                section_id=current_id,
                title=current_title,
                text=section_body(current_lines),
                start_page=current_start_page,
                end_page=current_end_page,
            )
        )

    return sections


def parse(
    input_path: Path,
    output_path: Path,
    *,
    first_section_pattern: str | None = None,
    section_pattern: str | None = None,
    end_marker: str | None = None,
) -> list[LegalSection]:
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with input_path.open(encoding="utf-8") as file:
        records = [json.loads(line) for line in file if line.strip()]

    sections = parse_sections(
        records,
        first_section_pattern=first_section_pattern,
        section_pattern=section_pattern,
        end_marker=end_marker,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            [asdict(section) for section in sections],
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Sections parsed: {len(sections)}")
    print(f"Output: {output_path}")
    print(f"First section: {sections[0].title if sections else 'None'}")
    print(f"Last section: {sections[-1].section_id if sections else 'None'}")

    return sections
