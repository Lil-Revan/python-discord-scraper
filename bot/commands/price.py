from __future__ import annotations

import logging

import discord
from discord import app_commands

from bot.services.crypto_service import (
    CoinGeckoCryptoService,
    CryptoServiceError,
    MissingPriceDataError,
    UnsupportedSymbolError,
)
from bot.services.graph_generator import render_price_chart

logger = logging.getLogger(__name__)


def _format_change_line(price_change_24h: float | None) -> str:
    if price_change_24h is None:
        return "24h change: unavailable"

    arrow = "+" if price_change_24h >= 0 else ""
    return f"24h change: **{arrow}{price_change_24h:.2f}%**"


def build_price_command(crypto_service: CoinGeckoCryptoService) -> app_commands.Command:
    @app_commands.command(
        name="price",
        description="Fetch the recent price trend for a cryptocurrency.",
    )
    @app_commands.describe(symbol="Crypto symbol such as BTC, ETH, SOL, XRP, ADA, or DOGE.")
    async def price(interaction: discord.Interaction, symbol: str) -> None:
        await interaction.response.defer(thinking=True)
        normalized_symbol = symbol.strip().upper()

        try:
            snapshot = await crypto_service.get_snapshot(normalized_symbol)
            chart = render_price_chart(snapshot)
        except UnsupportedSymbolError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        except MissingPriceDataError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        except CryptoServiceError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        except Exception:
            logger.exception("Unexpected failure while handling /price for %s", normalized_symbol)
            await interaction.followup.send(
                "Something went wrong while fetching crypto market data.",
                ephemeral=True,
            )
            return

        filename = f"{snapshot.symbol.lower()}-{snapshot.vs_currency.lower()}-price.png"
        file = discord.File(chart, filename=filename)
        summary = (
            f"**{snapshot.name} ({snapshot.symbol})**\n"
            f"Current price: **{snapshot.current_price:,.4f} {snapshot.vs_currency.upper()}**\n"
            f"{_format_change_line(snapshot.price_change_24h)}\n"
            f"History window: **{len(snapshot.points)} days**\n"
            f"Source: {snapshot.source_name} - <{snapshot.source_url}>"
        )
        await interaction.followup.send(content=summary, file=file)

    return price
