from pathlib import Path

from langchain.agents import create_agent

from ..kg import KnowledgeGraph
from .tools import build_tools

PROMPT = (Path(__file__).parent / "AGENTS.md").read_text(
    encoding="utf-8"
)


def build_agent(kg: KnowledgeGraph, graph, chat_model=None):
    """Build the LangChain tool-calling agent over the knowledge graph."""
    from ..models import model

    return create_agent(
        model=chat_model or model,
        tools=build_tools(kg, graph),
        system_prompt=PROMPT,
    )
