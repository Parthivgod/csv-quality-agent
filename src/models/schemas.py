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


class Interpretation(BaseModel):
    """Model interpretation linked to observable tool results, not a new finding."""
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=1600)
    source_tools: list[str] = Field(min_length=1, max_length=6)


class DataQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2400)
    issues: list[Issue] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    interpretation: list[Interpretation] = Field(default_factory=list, max_length=6)
    next_steps: list[str] = Field(default_factory=list, max_length=6)
    assessment_summary: str = ""
