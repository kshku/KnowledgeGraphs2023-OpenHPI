from knowledgegraphs2023_openhpi import config


def test_paths_and_constants():
    assert config.DOCUMENTS_PATH.name == "documents.json"
    assert config.GENERATED_ONTOLOGY_PATH.name == "legal-documents.rdf"
    assert config.GENERATED_ONTOLOGY_PATH.parent.name == "generated"
    assert config.ONTOLOGY_IRI == "https://example.org/legal-ontology"
    assert config.DATA_ONTOLOGY_IRI.endswith("/data/legal-documents")
    assert config.PARSED_DIR.name == "parsed"
