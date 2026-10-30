from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
DOCUMENTS_PATH = DATA_DIR / "documents.json"
EXTRACTED_DIR = DATA_DIR / "extracted"
PARSED_DIR = DATA_DIR / "parsed"

ONTOLOGY_DIR = PROJECT_ROOT / "ontology"
GENERATED_DIR = ONTOLOGY_DIR / "generated"
GENERATED_ONTOLOGY_PATH = GENERATED_DIR / "consumer-protection-individuals.rdf"
ONTOLOGY_SCHEMA_PATH = ONTOLOGY_DIR / "legal-ontology.rdf"

ONTOLOGY_IRI = "https://example.org/legal-ontology"
DATA_ONTOLOGY_IRI = f"{ONTOLOGY_IRI}/data/consumer-protection-2019"

ACT_TITLE = "The Consumer Protection Act, 2019"
ACT_SOURCE_URL = (
    "https://indiacode.gov.in/pdf-viewer/"
    "1b6c1754-47b1-411e-9607-1712a9caf368/"
    "b5ba879f-4662-458c-b5d3-dae377ff92e0"
)

EXPECTED_SECTION_COUNT = 107
