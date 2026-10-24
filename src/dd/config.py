"""Application configuration — loads .env and exposes a typed Settings object."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env from project root (two levels up from src/dd/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    """Typed configuration loaded from environment variables."""

    # --- Mode ---
    sample_mode: bool = Field(default=True, alias="SAMPLE_MODE")

    # --- Nightshift (LLM provider) ---
    nightshift_base_url: str = Field(
        default="https://placeholder.example.com/v1",
        alias="NIGHTSHIFT_BASE_URL",
    )
    nightshift_api_key: str = Field(default="", alias="NIGHTSHIFT_API_KEY")

    # --- Model IDs ---
    model_extractor: str = Field(default="sample-stub", alias="MODEL_EXTRACTOR")
    model_redteam: str = Field(default="sample-stub", alias="MODEL_REDTEAM")
    model_verifier: str = Field(default="sample-stub", alias="MODEL_VERIFIER")

    # --- Zetaris ---
    zetaris_host: str = Field(default="localhost", alias="ZETARIS_HOST")
    zetaris_port: int = Field(default=5432, alias="ZETARIS_PORT")
    zetaris_user: str = Field(default="", alias="ZETARIS_USER")
    zetaris_password: str = Field(default="", alias="ZETARIS_PASSWORD")
    zetaris_database: str = Field(default="", alias="ZETARIS_DATABASE")
    zetaris_jdbc_url: str = Field(default="", alias="ZETARIS_JDBC_URL")

    # --- Linker Constants ---
    linker_gps_radius_meters: float = Field(default=100.0, alias="LINKER_GPS_RADIUS_METERS")
    linker_time_window_minutes: float = Field(default=30.0, alias="LINKER_TIME_WINDOW_MINUTES")

    # --- Paths ---
    project_root: Path = _PROJECT_ROOT
    data_dir: Path = _PROJECT_ROOT / "data" / "sample"
    runs_dir: Path = _PROJECT_ROOT / "runs"
    cache_dir: Path = _PROJECT_ROOT / "cache"

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}



def get_settings() -> Settings:
    """Return a Settings instance (can be overridden in tests)."""
    return Settings()
