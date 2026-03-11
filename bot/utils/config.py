from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    vs_currency: str = "usd"
    history_days: int = 30
    coingecko_api_key: str | None = None

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()

        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is missing from the environment.")

        vs_currency = os.getenv("CRYPTO_VS_CURRENCY", "usd").strip().lower() or "usd"

        history_days_raw = os.getenv("CRYPTO_HISTORY_DAYS", "30").strip()
        try:
            history_days = max(7, min(90, int(history_days_raw)))
        except ValueError as error:
            raise RuntimeError("CRYPTO_HISTORY_DAYS must be an integer.") from error

        coingecko_api_key = os.getenv("COINGECKO_API_KEY", "").strip() or None

        return cls(
            bot_token=bot_token,
            vs_currency=vs_currency,
            history_days=history_days,
            coingecko_api_key=coingecko_api_key,
        )
