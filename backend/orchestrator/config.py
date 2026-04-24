"""Auto-Negotiate Backend Configuration."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    HOST: str = "0.0.0.0"
    PORT: int = 8100
    DEBUG: bool = True

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3000",
    ]

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4o"

    MAX_NEGOTIATION_ROUNDS: int = 8
    AGENT_TIMEOUT: int = 60  # seconds per agent call

    # Market value tolerance band
    MARKET_TOLERANCE_LOW: float = 0.5   # 50% of predicted
    MARKET_TOLERANCE_HIGH: float = 2.0  # 200% of predicted


settings = Settings()
