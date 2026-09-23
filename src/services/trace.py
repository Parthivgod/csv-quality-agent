"""Observable tool-call events only; no model reasoning is stored."""

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class TraceCollector:
    max_calls: int
    events: list[dict] = field(default_factory=list)
    lock: Lock = field(default_factory=Lock, repr=False)

    def add(self, tool: str, arguments: dict, result: dict) -> None:
        self.events.append({"sequence": len(self.events) + 1, "tool": tool,
                            "arguments": arguments, "status": result.get("status", "error"),
                            "summary": result.get("summary", "No summary"),
                            "result": result})

    @property
    def used(self) -> list[str]:
        return [e["tool"] for e in self.events if e["status"] != "budget_exceeded"]
