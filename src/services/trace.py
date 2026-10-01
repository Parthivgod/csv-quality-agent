"""Tool-call evidence and brief user-facing selection explanations."""

from dataclasses import dataclass, field
from threading import Lock
import unicodedata


def normalize_selection_reason(value: str) -> str:
    """Keep a brief plain-text explanation; omit control/format characters."""
    if not isinstance(value, str):
        raise ValueError("Tool selection reason must be plain text.")
    cleaned = " ".join("".join(
        " " if unicodedata.category(character).startswith("C") else character
        for character in value).split())
    if len(cleaned) > 300:
        raise ValueError("Tool selection reason must be at most 300 characters.")
    return cleaned


@dataclass
class TraceCollector:
    max_calls: int
    events: list[dict] = field(default_factory=list)
    lock: Lock = field(default_factory=Lock, repr=False)
    full_results: list[dict] = field(default_factory=list, repr=False)
    executed_calls: int = 0
    local_compute_seconds: float = 0.0

    def add(self, tool: str, arguments: dict, result: dict) -> None:
        arguments = dict(arguments)
        reason = normalize_selection_reason(arguments.get("reason", ""))
        if "reason" in arguments:
            arguments["reason"] = reason
        self.events.append({"sequence": len(self.events) + 1, "tool": tool,
                            "arguments": arguments, "status": result.get("status", "error"),
                            "summary": result.get("summary", "No summary"),
                            "selection_reason": reason or None,
                            "result": result})

    @property
    def used(self) -> list[str]:
        return [e["tool"] for e in self.events if e["status"] != "budget_exceeded"]
