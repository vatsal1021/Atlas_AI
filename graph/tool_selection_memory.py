"""ToolSelectionMemory — Per-session tool performance tracker.

Used inside ReactNode to help it prefer reliable tools and avoid
recently failed ones. Not a graph node — purely a helper class.
"""

from __future__ import annotations

from typing import Any


class ToolSelectionMemory:
    """Tracks tool success rates, latency, and failure history for one session."""

    def __init__(self, data: dict[str, Any] | None = None):
        self.data: dict[str, dict] = data or {}

    def record(self, tool_name: str, success: bool, latency: float) -> None:
        """Record one tool execution outcome."""
        if tool_name not in self.data:
            self.data[tool_name] = {
                "calls": 0,
                "successes": 0,
                "failures": 0,
                "total_latency": 0.0,
                "last_status": None,
            }
        entry = self.data[tool_name]
        entry["calls"] += 1
        entry["total_latency"] += latency
        entry["last_status"] = "success" if success else "failure"
        if success:
            entry["successes"] += 1
        else:
            entry["failures"] += 1

    def success_rate(self, tool_name: str) -> float:
        entry = self.data.get(tool_name)
        if not entry or entry["calls"] == 0:
            return 1.0   # assume reliable if never tried
        return entry["successes"] / entry["calls"]

    def avg_latency(self, tool_name: str) -> float:
        entry = self.data.get(tool_name)
        if not entry or entry["calls"] == 0:
            return 0.0
        return entry["total_latency"] / entry["calls"]

    def summary(self) -> str:
        """One-line summary for inclusion in the ReAct prompt."""
        if not self.data:
            return "No tools used yet this session."
        lines = []
        for tool, entry in self.data.items():
            rate = entry["successes"] / max(entry["calls"], 1)
            lines.append(
                f"  {tool}: {entry['calls']} call(s), "
                f"{rate:.0%} success, "
                f"last={entry['last_status']}"
            )
        return "\n".join(lines)
