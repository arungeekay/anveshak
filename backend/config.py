"""Runtime configuration (env-driven; never hardcode secrets). See CLAUDE.md."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_version: str = "0.1.0"
    environment: str = "dev"

    # Data layer (ADR-1: DuckDB analytical mirror)
    duckdb_path: str = str(REPO_ROOT / "build" / "anveshak.duckdb")
    data_seed: int = 42

    # LLM (ADR-4). backend = quickml | ollama
    llm_backend: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    quickml_endpoint: str = ""
    quickml_api_key: str = ""

    # Embeddings (ADR-5)
    embed_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # Catalyst
    catalyst_project_id: str = ""
    catalyst_dc: str = "in"

    @property
    def duckdb_file(self) -> Path:
        return Path(self.duckdb_path)


settings = Settings()
