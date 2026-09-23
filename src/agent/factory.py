"""One swappable chat-model factory and LangChain agent constructor."""

import os

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel

from src.agent.prompt import AGENT_PROMPT
from src.config import Settings


def create_chat_model(settings: Settings) -> BaseChatModel:
    """Create a provider model without exposing or embedding the API key."""
    if settings.provider == "mistral":
        if not os.getenv("MISTRAL_API_KEY"):
            raise ValueError("MISTRAL_API_KEY is missing. Set it in .env before running triage.")
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(model=settings.model, temperature=0)
    if settings.provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is missing. Set it in .env before running triage.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=settings.model, temperature=0)
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.provider}. Choose mistral or openai.")


def create_investigation_agent(model: BaseChatModel, tools: list, context: dict,
                               target: str | None, settings: Settings):
    """Use the current LangChain create_agent API with a rendered prompt template."""
    descriptions = "\n".join(f"- {tool.name}: {tool.description}" for tool in tools)
    system_prompt = AGENT_PROMPT.format_messages(
        max_tool_calls=settings.max_tool_calls, tool_descriptions=descriptions,
        dataset_context=str(context), target_column=target or "none")[0].content
    return create_agent(model=model, tools=tools, system_prompt=system_prompt)
