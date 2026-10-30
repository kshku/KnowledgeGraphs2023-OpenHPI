from knowledgegraphs2023_openhpi import config


def test_paths_and_constants():
    assert config.EXPECTED_SECTION_COUNT == 107
    assert config.GENERATED_ONTOLOGY_PATH.name == "consumer-protection-individuals.rdf"
    assert config.GENERATED_ONTOLOGY_PATH.parent.name == "generated"
    assert config.ONTOLOGY_IRI == "https://example.org/legal-ontology"
    assert config.PARSED_DIR.name == "parsed"
