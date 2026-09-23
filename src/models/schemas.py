"""Structured report schema."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue: str
    severity: Literal["low", "medium", "high"]
    column: str | None = None
    evidence: str
    impact: str
    recommendation: str
    source_tool: str


class DataQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    issues: list[Issue] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
