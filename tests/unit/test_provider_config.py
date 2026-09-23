import pandas as pd
import pytest

from src.agent.factory import create_chat_model, create_investigation_agent
from src.agent.tools import build_tools
from src.config import Settings, provider_key_name, provider_ready
from src.services.trace import TraceCollector


def test_groq_key_readiness(monkeypatch) -> None:
    settings = Settings(provider="groq", model="openai/gpt-oss-120b")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert provider_key_name(settings) == "GROQ_API_KEY"
    assert not provider_ready(settings)
    with pytest.raises(ValueError, match="GROQ_API_KEY is missing"):
        create_chat_model(settings)
    monkeypatch.setenv("GROQ_API_KEY", "test-construction-only")
    assert provider_ready(settings)


def test_groq_model_and_agent_construct_without_api_call(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-construction-only")
    settings = Settings(provider="groq", model="openai/gpt-oss-120b")
    model = create_chat_model(settings)
    assert type(model).__name__ == "ChatGroq"
    tools = build_tools(pd.DataFrame({"age": [1, 2]}), None, settings, TraceCollector(6))
    assert model.bind_tools(tools) is not None
    agent = create_investigation_agent(model, tools, {"rows": 2}, None, settings)
    assert type(agent).__name__ == "CompiledStateGraph"
