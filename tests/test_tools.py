from knowledgegraphs2023_openhpi.agent.tools import build_tools


def test_tool_names_and_calls(kg):
    tools = {tool.name: tool for tool in build_tools(kg, kg.graph)}

    assert set(tools) == {
        "kg_get_schema",
        "kg_list_sections",
        "kg_get_section",
        "kg_find_sections",
        "kg_get_references",
        "kg_get_referenced_by",
        "kg_sparql",
    }

    assert (
        "Provision"
        in tools["kg_get_schema"].invoke({})["classes"]
    )
    assert (
        tools["kg_get_section"].invoke({"section_number": 2})["title"]
        == "Definitions"
    )
    assert (
        tools["kg_find_sections"].invoke({"query": "body"})[0]["number"]
        == 1
    )
    assert tools["kg_get_referenced_by"].invoke({"section_number": 2}) == [1]
