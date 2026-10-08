from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _float_env(key: str, default: float = 0.0) -> float:
    val = os.getenv(key, "")
    return float(val) if val else default


def _int_env(key: str, default: int) -> int:
    val = os.getenv(key, "")
    return int(val) if val else default


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    llm_enabled: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
    llm_polish_default: bool = os.getenv("LLM_POLISH_DEFAULT", "false").lower() == "true"
    gemini_price_in_per_m: float = _float_env("GEMINI_PRICE_IN_PER_M")
    gemini_price_out_per_m: float = _float_env("GEMINI_PRICE_OUT_PER_M")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = _int_env("API_PORT", 8000)
    project_root: Path = _PROJECT_ROOT

    def __repr__(self) -> str:
        return (
            f"Settings(gemini_model={self.gemini_model!r}, "
            f"llm_enabled={self.llm_enabled}, api_host={self.api_host}, "
            f"api_port={self.api_port})"
        )


settings = Settings()
