from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # Owner identity (used in agent prompts — never hardcode real name in code)
    owner_name: str = "Shay"

    # Telegram
    telegram_bot_token: str = ""
    telegram_owner_chat_id: str = ""

    # Weather
    openweathermap_api_key: str = ""
    weather_city: str = "Israel"

    # Scheduling
    briefing_hour: int = 7
    briefing_minute: int = 30

    # Agent Tools — Phase D
    tavily_api_key: str = ""          # https://app.tavily.com (free: 1000/month)
    brave_search_api_key: str = ""    # https://brave.com/search/api/ (free: 2000/month)
    exa_api_key: str = ""             # https://exa.ai (free: 1000/month)
    n8n_webhook_base_url: str = "http://localhost:5678"

    # Paths
    ledgeralpha_signals_path: str = ""
    bash_log_path: str = ""
    lessons_path: str = "./docs/archive"
    projects_base_path: str = ""
    github_token: str = ""  # optional — raises rate limit to 5000/hr if set

    # Gmail
    gmail_email: str = ""
    gmail_app_password: str = ""  # Google App Password (not account password)

    # Voice
    wake_word: str = "hey jarvis"
    voice_enabled: bool = False

    # Regime Guard
    regime_check_interval_hours: int = 2
    regime_alert_threshold: float = -0.6


settings = Settings()
