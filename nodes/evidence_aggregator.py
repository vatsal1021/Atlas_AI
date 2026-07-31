"""Evidence Aggregator node.

Deterministic merge of raw tool_results into a structured evidence dict
organised by category.  No LLM call.
"""

from __future__ import annotations

import logging
from datetime import datetime

from graph.state import TripState

logger = logging.getLogger(__name__)

# Map tool names to evidence categories
_TOOL_TO_CATEGORY: dict[str, str] = {
    "search_flights": "flights",
    "search_hotels": "hotels",
    "get_weather": "weather",
    "check_constraints": "constraints",
}


def evidence_aggregator(state: TripState) -> dict:
    """Merge tool results into structured evidence by category.

    Returns
    -------
    dict
        Partial state with updated ``evidence``.
    """
    tool_results = state.get("tool_results", {})
    existing_evidence = dict(state.get("evidence", {}))

    logger.info(
        "evidence_aggregator  tool_result_keys=%s",
        list(tool_results.keys()),
    )

    timestamp = datetime.now().isoformat()

    for tool_name, results in tool_results.items():
        category = _TOOL_TO_CATEGORY.get(tool_name, tool_name)

        if category not in existing_evidence:
            existing_evidence[category] = {
                "items": [],
                "last_updated": timestamp,
                "source_tool": tool_name,
            }

        # Merge items, deduplicate by a simple content hash
        existing_items = existing_evidence[category]["items"]
        existing_keys = {_item_key(item) for item in existing_items}

        if isinstance(results, list):
            for item in results:
                key = _item_key(item)
                if key not in existing_keys:
                    existing_items.append(item)
                    existing_keys.add(key)
        else:
            key = _item_key(results)
            if key not in existing_keys:
                existing_items.append(results)

        existing_evidence[category]["last_updated"] = timestamp
        logger.info(
            "Category '%s' now has %d items",
            category, len(existing_items),
        )

    return {"evidence": existing_evidence}


def _item_key(item: dict | object) -> str:
    """Generate a simple dedup key from an item."""
    if isinstance(item, dict):
        # Use a subset of fields for dedup
        parts = []
        for k in sorted(item.keys()):
            if k in ("name", "flight_number", "date", "airline", "location"):
                parts.append(f"{k}={item[k]}")
        return "|".join(parts) if parts else str(hash(str(item)))
    return str(hash(str(item)))
