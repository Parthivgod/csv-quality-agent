"""Environment-backed application settings and diagnostic heuristics."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()

PROVIDER_API_KEYS = {
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openai": "OPENAI_API_KEY",
}


@dataclass(frozen=True)
class Settings:
    provider: str = os.getenv("LLM_PROVIDER", "groq").lower()
    model: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    max_tool_calls: int = int(os.getenv("MAX_TOOL_CALLS", "6"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "250"))
    missing_medium_pct: float = float(os.getenv("MISSING_MEDIUM_PCT", "5"))
    missing_high_pct: float = float(os.getenv("MISSING_HIGH_PCT", "30"))
    near_constant_ratio: float = float(os.getenv("NEAR_CONSTANT_RATIO", "0.95"))
    high_cardinality_ratio: float = float(os.getenv("HIGH_CARDINALITY_RATIO", "0.90"))
    high_cardinality_min_non_null: int = int(os.getenv("HIGH_CARDINALITY_MIN_NON_NULL", "20"))
    correlation_threshold: float = float(os.getenv("CORRELATION_THRESHOLD", "0.95"))
    pandas_threshold_mb: int = int(os.getenv("PANDAS_THRESHOLD_MB", "20"))
    duckdb_memory_limit: str = os.getenv("DUCKDB_MEMORY_LIMIT", "1GB")
    duckdb_threads: int = int(os.getenv("DUCKDB_THREADS", "2"))
    duckdb_spill_limit_mb: int = int(os.getenv("DUCKDB_SPILL_LIMIT_MB", "2048"))
    session_temp_limit_mb: int = int(os.getenv("SESSION_TEMP_LIMIT_MB", "4096"))
    max_numeric_columns: int = int(os.getenv("MAX_NUMERIC_COLUMNS", "20"))
    query_timeout_seconds: float = float(os.getenv("QUERY_TIMEOUT_SECONDS", "120"))
    import_timeout_seconds: float = float(os.getenv("IMPORT_TIMEOUT_SECONDS", "120"))
    max_local_compute_seconds: float = float(os.getenv("MAX_LOCAL_COMPUTE_SECONDS", "180"))
    max_tool_attempts: int = int(os.getenv("MAX_TOOL_ATTEMPTS", "12"))
    max_observation_bytes: int = int(os.getenv("MAX_OBSERVATION_BYTES", "16384"))
    max_findings_per_tool: int = int(os.getenv("MAX_FINDINGS_PER_TOOL", "20"))
    max_schema_columns: int = int(os.getenv("MAX_SCHEMA_COLUMNS", "50"))

    def __post_init__(self) -> None:
        if self.max_tool_calls < 1 or self.max_upload_mb < 1:
            raise ValueError("MAX_TOOL_CALLS and MAX_UPLOAD_MB must be positive")
        if min(self.pandas_threshold_mb, self.duckdb_threads, self.duckdb_spill_limit_mb,
               self.session_temp_limit_mb, self.max_numeric_columns, self.max_tool_attempts,
               self.max_findings_per_tool, self.max_schema_columns) < 1:
            raise ValueError("Dataset resource settings must be positive")
        if self.max_observation_bytes < 2048:
            raise ValueError("MAX_OBSERVATION_BYTES must be at least 2048")
        if min(self.query_timeout_seconds, self.import_timeout_seconds, self.max_local_compute_seconds) <= 0:
            raise ValueError("Dataset time limits must be positive")
        if not 0 <= self.missing_medium_pct < self.missing_high_pct <= 100:
            raise ValueError("Missing-value thresholds must be increasing percentages")
        for value in (self.near_constant_ratio, self.high_cardinality_ratio, self.correlation_threshold):
            if not 0 < value <= 1:
                raise ValueError("Ratio thresholds must be in (0, 1]")


def provider_ready(settings: Settings) -> bool:
    key = provider_key_name(settings)
    return bool(os.getenv(key)) if key else False


def provider_key_name(settings: Settings) -> str | None:
    """Return the environment variable needed by the selected provider."""
    return PROVIDER_API_KEYS.get(settings.provider)
