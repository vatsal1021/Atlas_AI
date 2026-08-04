"""Prompt loader utility.

Loads structured prompt definitions from YAML files under ``prompts/``.
Each YAML file must contain two top-level keys:

    system_prompt: |
        Static role definition / persona for the SystemMessage.
        No template variables here.

    user_prompt: |
        Dynamic context template for the HumanMessage.
        Use {variable_name} placeholders for runtime values.

Usage in a node::

    from services.prompt_loader import load_prompt

    system_prompt, user_template = load_prompt("goal_understanding")
    user_content = user_template.format(user_input=..., memory_context=...)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=32)
def load_prompt(name: str) -> tuple[str, str]:
    """Load a prompt definition from ``prompts/<name>.yaml``.

    Parameters
    ----------
    name : str
        Prompt name without extension, e.g. ``"goal_understanding"``.

    Returns
    -------
    tuple[str, str]
        ``(system_prompt, user_prompt_template)``

        - ``system_prompt`` is ready to use as-is (no variables).
        - ``user_prompt_template`` contains ``{variable}`` placeholders;
          call ``.format(**kwargs)`` before passing to the LLM.

    Raises
    ------
    FileNotFoundError
        If the ``.yaml`` file does not exist.
    KeyError
        If the YAML is missing the ``system_prompt`` or ``user_prompt`` keys.
    """
    path = _PROMPTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {path}\n"
            f"Expected a YAML file at prompts/{name}.yaml"
        )

    raw = path.read_text(encoding="utf-8")
    data: dict = yaml.safe_load(raw)

    if "system_prompt" not in data:
        raise KeyError(f"prompts/{name}.yaml is missing the 'system_prompt' key.")
    if "user_prompt" not in data:
        raise KeyError(f"prompts/{name}.yaml is missing the 'user_prompt' key.")

    system_prompt: str = data["system_prompt"].strip()
    user_prompt: str = data["user_prompt"].strip()

    logger.debug("Loaded prompt '%s' (sys=%d chars, user=%d chars)", name, len(system_prompt), len(user_prompt))
    return system_prompt, user_prompt
