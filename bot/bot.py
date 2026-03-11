from __future__ import annotations

import logging

import aiohttp
import discord
from discord.ext import commands

from bot.commands.price import build_price_command
from bot.services.crypto_service import CoinGeckoCryptoService
from bot.utils.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CryptoPriceBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.http_session: aiohttp.ClientSession | None = None
        self.crypto_service: CoinGeckoCryptoService | None = None

    async def setup_hook(self) -> None:
        timeout = aiohttp.ClientTimeout(total=30)
        self.http_session = aiohttp.ClientSession(timeout=timeout)
        self.crypto_service = CoinGeckoCryptoService(
            session=self.http_session,
            vs_currency=self.settings.vs_currency,
            history_days=self.settings.history_days,
            api_key=self.settings.coingecko_api_key,
        )
        self.tree.add_command(build_price_command(self.crypto_service))
        await self.tree.sync()
        logger.info("Slash commands synced successfully.")

    async def close(self) -> None:
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
        await super().close()


def run() -> None:
    settings = Settings.load()
    client = CryptoPriceBot(settings)
    client.run(settings.bot_token)


if __name__ == "__main__":
    run()
