"""Application settings.

Every default that affects behaviour, scoring, security or data handling is listed in
docs/DECISION_LOG.md (defaults register, DD-xx) and lives here or in versioned DB config —
never as a literal inside business logic (D-22).
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(ROOT / ".env"), ".env"), extra="ignore", env_file_encoding="utf-8"
    )

    app_env: str = "dev"
    database_url: str = "postgresql+psycopg://inhabitr_app:inhabitr_app_dev@localhost:5433/inhabitr"
    database_owner_url: str = "postgresql+psycopg://inhabitr_owner:inhabitr_owner_dev@localhost:5433/inhabitr"

    # Security (DD-17)
    secret_key: str = "dev-secret-change-me"
    cookie_secure: bool = False
    session_idle_days: int = 7
    session_absolute_days: int = 30
    login_rate_limit_per_min: int = 5
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    # Separate frontend (D-35/D-36): Lovable-hosted previews and apps may call the API from these origins.
    # Plus any localhost port, so the app can also be run (or a demo recorded) on this machine without a tunnel.
    cors_origin_regex: str | None = (r"https://([a-z0-9-]+\.)*(lovable\.app|lovableproject\.com|lovable\.dev)"
                                     r"|http://(localhost|127\.0\.0\.1)(:\d+)?")
    # Bearer-token sessions for a frontend on another site (cookies are blocked cross-site by many browsers).
    token_auth_enabled: bool = True

    # AI (D-05, D-32). Provider is swappable; Gemini is the default.
    llm_provider: str = "gemini"  # "gemini" | "openai"
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    openai_api_key: str | None = None
    # Empty -> provider default (see llm_default_models).
    llm_model_fast: str | None = None
    llm_model_standard: str | None = None
    # Requests per minute the AI key allows (D-44). 0 = no limit. Free Gemini keys: about 10.
    llm_max_rpm: int = 0
    llm_timeout_s: int = 120
    llm_default_models: dict[str, dict[str, str]] = {
        "gemini": {"fast": "gemini-2.5-flash", "standard": "gemini-2.5-flash"},
        "openai": {"fast": "gpt-5-mini", "standard": "gpt-5-mini"},
    }
    # USD per 1M tokens (input, output). Placeholders - verify against current vendor pricing.
    # Gemini thinking tokens are billed as output and are counted as output here.
    llm_pricing: dict[str, tuple[float, float]] = {
        "gemini-2.5-flash": (0.30, 2.50),
        "gemini-2.5-flash-lite": (0.10, 0.40),
        "gemini-2.5-pro": (1.25, 10.00),
        "gpt-5-mini": (0.25, 2.00),
        "gpt-5": (1.25, 10.00),
        "gpt-5-nano": (0.05, 0.40),
        "gpt-4.1-mini": (0.40, 1.60),
        "gpt-4o-mini": (0.15, 0.60),
    }

    # Providers (P-06)
    tavily_api_key: str | None = None
    tavily_cost_per_search_usd: float = 0.008
    http_user_agent: str = "HaloBot/0.1 (B2B account research; respects robots.txt)"
    overpass_endpoints: list[str] = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]
    overpass_timeout_s: int = 90
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    gdelt_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    gdelt_min_interval_s: float = 5.5
    fetch_timeout_s: float = 12.0
    fetch_max_bytes: int = 2_000_000
    fetch_per_domain_interval_s: float = 1.0

    # Evidence (DD-12)
    grounding_fuzzy_threshold: int = 92
    grounding_stale_years: int = 3

    # Research budgets (DD-18) — placeholders until measured
    research_depths: dict[str, dict[str, float]] = {
        "light": {"max_tool_calls": 3, "max_pages": 3, "max_cost_usd": 0.05},
        "standard": {"max_tool_calls": 7, "max_pages": 6, "max_cost_usd": 0.15},
    }
    page_text_chars_for_llm: int = 7000

    # Limits (DD-16)
    max_companies_per_job: int = 200
    worker_concurrency: int = 4
    # Automatic first run when a project is created (D-40). Small on purpose: it spends AI quota without a click.
    autostart_max_companies: int = 50
    autostart_budget_usd: float = 2.0
    job_wall_clock_hours: float = 3.0
    default_budget_usd: float = 5.0
    task_lease_seconds: int = 180

    # Estimates (DD-20)
    estimate_pass_rate: float = 0.5
    estimate_multipliers: tuple[float, float, float] = (0.6, 1.0, 1.8)
    estimate_cost_per_company_usd: dict[str, float] = {"light": 0.01, "standard": 0.03}
    estimate_seconds_per_company: dict[str, float] = {"light": 25, "standard": 60}

    # Retention (DD-13)
    page_text_retention_days: int = 90

    @property
    def llm_api_key(self) -> str | None:
        return self.gemini_api_key if self.llm_provider == "gemini" else self.openai_api_key

    @property
    def llm_key_name(self) -> str:
        return "GEMINI_API_KEY" if self.llm_provider == "gemini" else "OPENAI_API_KEY"

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key)

    def llm_model(self, tier: str) -> str:
        explicit = self.llm_model_standard if tier == "standard" else self.llm_model_fast
        defaults = self.llm_default_models.get(self.llm_provider, self.llm_default_models["gemini"])
        return explicit or defaults["standard" if tier == "standard" else "fast"]

    @property
    def search_configured(self) -> bool:
        return bool(self.tavily_api_key)

    @property
    def session_cookie_name(self) -> str:
        return "__Host-halo_session" if self.cookie_secure else "halo_session"


@lru_cache
def get_settings() -> Settings:
    return Settings()
