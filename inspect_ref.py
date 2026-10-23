import json
import re
from pathlib import Path

input_path = Path("data/parsed/A2019-35.jsonl")

with input_path.open(encoding="utf-8") as file:
    sections = json.load(file)

# Initial heuristic: explicit references such as "section 10".
pattern = re.compile(r"\bsections?\s+(\d+)\b", re.IGNORECASE)

match_count = 0

for section in sections:
    text = section["text"]

    for match in pattern.finditer(text):
        target_number = int(match.group(1))
        start = max(0, match.start() - 60)
        end = min(len(text), match.end() + 60)

        print(
            f"Source section {section['number']} "
            f"-> candidate section {target_number}"
        )
        print(f"  ...{text[start:end].replace(chr(10), ' ')}...")
        match_count += 1

        if match_count >= 30:
            break

    if match_count >= 30:
        break

print(f"\nDisplayed {match_count} candidate references.")
