import json
from pathlib import Path

path = Path("data/parsed/A2019-35.jsonl")
sections = json.loads(path.read_text(encoding="utf-8"))

numbers = [section["number"] for section in sections]

print("Total sections:", len(sections))
print("First section:", numbers[0])
print("Last section:", numbers[-1])
print("Duplicate section numbers:", sorted({
    n for n in numbers if numbers.count(n) > 1
}))
print("Missing section numbers:", sorted(set(range(1, 108)) - set(numbers)))

for section in sections:
    if not section["text"].strip():
        print("Empty section:", section["number"], section["title"])

for number in (1, 2, 3, 107):
    matches = [s for s in sections if s["number"] == number]
    for section in matches:
        print(
            f"Section {number}: {section['title']!r}, "
            f"pages {section['start_page']}-{section['end_page']}, "
            f"{len(section['text'])} characters"
        )

section = next(s for s in sections if s["number"] == 2)

lines = section["text"].splitlines()

print("First 5 lines:")
for line in lines[:5]:
    print(repr(line))

print("\nLast 10 lines:")
for line in lines[-10:]:
    print(repr(line))
