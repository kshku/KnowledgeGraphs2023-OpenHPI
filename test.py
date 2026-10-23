import json
from pathlib import Path

path = Path("data/parsed/A2019-35.jsonl")
sections = json.loads(path.read_text(encoding='utf-8'))

for section in sections:
    lines = section["text"].splitlines()
    trailing = [
        line.strip()
        for line in lines[-4:]
        if line.strip().startswith("CHAPTER ")
        or line.strip().isupper()
    ]
    if trailing:
        print(f"\nSection {section['number']}: {section['title']}")
        print("Trailing headings:", trailing)


for number in (2, 9, 27, 73, 81, 93, 107):
    section = next(s for s in sections if s["number"] == number)
    print(f"\nSection {number}: {section['title']}")
    print("\n".join(section["text"].splitlines()[-4:]))
