"""Auto-Negotiate Backend Configuration."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8100"))  # Render injects $PORT automatically
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Comma-separated origins via ALLOWED_ORIGINS env var, or use defaults
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv(
            "ALLOWED_ORIGINS",
            ",".join([
                "http://localhost:3000",
                "http://localhost:3100",
                "http://localhost:6900",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:6900",
                "https://frontend-amber-zeta-13.vercel.app",
            ]),
        ).split(",")
        if o.strip()
    ]

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4o-mini"

    MAX_NEGOTIATION_ROUNDS: int = 8
    AGENT_TIMEOUT: int = 60  # seconds per agent call

    MARKET_TOLERANCE_LOW: float = 0.5
    MARKET_TOLERANCE_HIGH: float = 2.0


settings = Settings()
