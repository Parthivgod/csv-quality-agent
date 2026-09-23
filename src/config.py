"""Environment-backed application settings and diagnostic heuristics."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    provider: str = os.getenv("LLM_PROVIDER", "mistral").lower()
    model: str = os.getenv("LLM_MODEL", "mistral-small-latest")
    max_tool_calls: int = int(os.getenv("MAX_TOOL_CALLS", "6"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    missing_medium_pct: float = float(os.getenv("MISSING_MEDIUM_PCT", "5"))
    missing_high_pct: float = float(os.getenv("MISSING_HIGH_PCT", "30"))
    near_constant_ratio: float = float(os.getenv("NEAR_CONSTANT_RATIO", "0.95"))
    high_cardinality_ratio: float = float(os.getenv("HIGH_CARDINALITY_RATIO", "0.90"))
    high_cardinality_min_non_null: int = int(os.getenv("HIGH_CARDINALITY_MIN_NON_NULL", "20"))
    correlation_threshold: float = float(os.getenv("CORRELATION_THRESHOLD", "0.95"))

    def __post_init__(self) -> None:
        if self.max_tool_calls < 1 or self.max_upload_mb < 1:
            raise ValueError("MAX_TOOL_CALLS and MAX_UPLOAD_MB must be positive")
        if not 0 <= self.missing_medium_pct < self.missing_high_pct <= 100:
            raise ValueError("Missing-value thresholds must be increasing percentages")
        for value in (self.near_constant_ratio, self.high_cardinality_ratio, self.correlation_threshold):
            if not 0 < value <= 1:
                raise ValueError("Ratio thresholds must be in (0, 1]")


def provider_ready(settings: Settings) -> bool:
    key = "MISTRAL_API_KEY" if settings.provider == "mistral" else "OPENAI_API_KEY"
    return bool(os.getenv(key)) if settings.provider in {"mistral", "openai"} else False
