import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

SECTION_START = re.compile(
    r"^\s*(\d{1,3})\.\s+(.+)$"
)

FIRST_SECTION = re.compile(
    r"^\s*1\.\s*Short title,\s*extent,\s*commencement\s+"
    r"and application\.\s*[—–-]",
    re.IGNORECASE,
)

CHAPTER_HEADING = re.compile(r"^\s*CHAPTER\s+[IVXLCDM]+\s*$", re.IGNORECASE)


@dataclass
class LegalSection:
    number: int
    title: str
    text: str
    start_page: int
    end_page: int
    

def is_chapter_heading(line: str) -> bool:
    return bool(CHAPTER_HEADING.match(line.strip()))


def section_title(line: str) -> str:
    """Extract a section heading from its first line."""
    remainder = re.sub(r"^\s*\d{1,3}\.\s*", "", line).strip()

    # The Act's section headings use a dot followed by a dash
    # before the body text begins.
    title = re.split(r"\.\s*[—–-]", remainder, maxsplit=1)[0]

    return title.strip().rstrip(".")


def section_body(lines: list[str]) -> str:
    lines = lines.copy()

    while lines and not lines[-1].strip():
        lines.pop()

    # Remove chapter heading and its following title, if present.
    if lines and lines[-1].strip().isupper() and not is_chapter_heading(lines[-1]):
        if len(lines) >= 2 and is_chapter_heading(lines[-2]):
            lines = lines[:-2]

    return "\n".join(lines).strip()


def parse_sections(records: list[dict]) -> list[LegalSection]:
    sections: list[LegalSection] = []

    current_number: int | None = None
    current_title = ""
    current_lines: list[str] = []
    start_page = 0
    end_page = 0
    started = False

    for record in records:
        page_number = record["page"]

        for line in record["text"].splitlines():
            if not started:
                if FIRST_SECTION.match(line):
                    started = True
                else:
                    continue

            match = SECTION_START.match(line)

            if match:
                number = int(match.group(1))

                # Only accept the next expected top-level section.
                # This helps reject footnotes numbered 1, 2, etc.
                expected = 1 if current_number is None else current_number + 1

                if number == expected:
                    if current_number is not None:
                        sections.append(
                            LegalSection(
                                number=current_number,
                                title=current_title,
                                text=section_body(current_lines),
                                start_page=start_page,
                                end_page=end_page,
                            )
                        )

                    current_number = number
                    current_title = section_title(line)
                    current_lines = [line.strip()]
                    start_page = page_number
                    end_page = page_number
                    continue

            if current_number is not None:
                current_lines.append(line.rstrip())
                end_page = page_number

    if current_number is not None:
        sections.append(
            LegalSection(
                number=current_number,
                title=current_title,
                text=section_body(current_lines),
                start_page=start_page,
                end_page=end_page,
            )
        )

    return sections

def parse(input_path: Path, output_path: Path) -> None:
    if not input_path.is_file():
        parser.error(f"Input file not found: {input_path}")

    with input_path.open(encoding="utf-8") as file:
        records = [json.loads(line) for line in file if line.strip()]

    sections = parse_sections(records)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            [asdict(section) for section in sections],
            file,
            ensure_ascii=False,
            indent=2,
        )

    numbers = [section.number for section in sections]
    missing = sorted(set(range(1, 108)) - set(numbers))

    print(f"Sections parsed: {len(sections)}")
    print(f"Output: {output_path}")
    print(f"First section: {sections[0].title if sections else 'None'}")
    print(f"Last section: {sections[-1].number if sections else 'None'}")
    print(f"Missing section numbers: {missing}")
