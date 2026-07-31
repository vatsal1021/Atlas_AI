"""LLM client factory.

Returns a LangChain chat model configured from application settings.
Supports OpenAI and Anthropic providers.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import get_settings

logger = logging.getLogger(__name__)


def get_llm(
    *,
    temperature: float | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Create and return a LangChain chat model based on application config.

    Parameters
    ----------
    temperature:
        Sampling temperature override.  Falls back to 0.3.
    model:
        Model identifier override.  Falls back to ``LLM_MODEL`` env var.
    **kwargs:
        Additional keyword arguments forwarded to the model constructor.

    Returns
    -------
    BaseChatModel
        A configured LangChain chat model instance.
    """
    settings = get_settings()
    provider = settings.llm_provider.lower()
    resolved_model = model or settings.llm_model
    resolved_temp = temperature if temperature is not None else 0.3

    logger.info(
        "Initialising LLM  provider=%s  model=%s  temperature=%s",
        provider,
        resolved_model,
        resolved_temp,
    )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=resolved_model,
            temperature=resolved_temp,
            api_key=settings.openai_api_key,
            **kwargs,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=resolved_model,
            temperature=resolved_temp,
            api_key=settings.anthropic_api_key,
            **kwargs,
        )

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=resolved_model,
            temperature=resolved_temp,
            api_key=settings.groq_api_key,
            **kwargs,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=resolved_model,
            temperature=resolved_temp,
            base_url=settings.ollama_base_url,
            **kwargs,
        )

    raise ValueError(
        f"Unsupported LLM provider '{provider}'. Must be 'openai', 'anthropic', 'groq', or 'ollama'."
    )
