from knowledgegraphs2023_openhpi import agent


def test_build_agent_uses_injected_model(monkeypatch, kg):
    captured = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return "agent"

    monkeypatch.setattr(agent, "create_agent", fake_create_agent)

    injected = object()

    result = agent.build_agent(kg, kg.graph, chat_model=injected)

    assert result == "agent"
    assert captured["model"] is injected
    assert [tool.name for tool in captured["tools"]][0] == "kg_get_schema"
