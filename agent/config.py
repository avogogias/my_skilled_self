"""Central configuration for the My Skilled Self agent."""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # Google ADK / Gemini
    google_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"))

    # FastAPI
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    cors_origins: list = field(default_factory=lambda: [
        o.strip() for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://frontend:3000"
        ).split(",") if o.strip()
    ])

    # Financial data
    alpha_vantage_api_key: str = field(default_factory=lambda: os.getenv("ALPHA_VANTAGE_API_KEY", "demo"))
    finnhub_api_key: str = field(default_factory=lambda: os.getenv("FINNHUB_API_KEY", ""))

    # GitHub reviewer skill
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    github_repo: str = field(default_factory=lambda: os.getenv("GITHUB_REPO", ""))

    # App
    app_name: str = "my_skilled_self"
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")


config = Config()
