from __future__ import annotations

import logging
from dataclasses import dataclass, replace

import discord
from discord import app_commands

from bot.services.crypto_service import (
    SUPPORTED_VS_CURRENCIES,
    CoinGeckoCryptoService,
    CryptoServiceError,
    CryptoSnapshot,
    MissingPriceDataError,
    UnsupportedCurrencyError,
    UnsupportedSymbolError,
)
from bot.services.graph_generator import format_price_label, render_price_chart

logger = logging.getLogger(__name__)
DEFAULT_QUOTE_CURRENCY = "usd"
_MESSAGE_TIMEOUT_SECONDS = 900


@dataclass(frozen=True)
class PriceRequestState:
    symbol: str
    quote_currency: str = DEFAULT_QUOTE_CURRENCY


class QuoteCurrencyButton(discord.ui.Button["PriceCurrencyView"]):
    def __init__(self, quote_currency: str, selected: bool) -> None:
        super().__init__(
            label=quote_currency.upper(),
            style=discord.ButtonStyle.primary if selected else discord.ButtonStyle.secondary,
            disabled=selected,
            row=0,
        )
        self.quote_currency = quote_currency

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is None:
            await interaction.response.send_message("This control is no longer available.", ephemeral=True)
            return

        await self.view.handle_currency_change(interaction, self.quote_currency)


class PriceCurrencyView(discord.ui.View):
    def __init__(self, crypto_service: CoinGeckoCryptoService, state: PriceRequestState) -> None:
        super().__init__(timeout=_MESSAGE_TIMEOUT_SECONDS)
        self.crypto_service = crypto_service
        self.state = state
        self.message: discord.Message | discord.WebhookMessage | None = None
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        self.clear_items()
        for quote_currency in SUPPORTED_VS_CURRENCIES:
            self.add_item(QuoteCurrencyButton(quote_currency, selected=quote_currency == self.state.quote_currency))

    async def handle_currency_change(self, interaction: discord.Interaction, quote_currency: str) -> None:
        try:
            snapshot = await self.crypto_service.get_snapshot(self.state.symbol, vs_currency=quote_currency)
        except (UnsupportedSymbolError, UnsupportedCurrencyError, MissingPriceDataError, CryptoServiceError) as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        except Exception:
            logger.exception(
                "Unexpected failure while updating /price for %s in %s",
                self.state.symbol,
                quote_currency,
            )
            await interaction.response.send_message(
                "Something went wrong while updating the chart.",
                ephemeral=True,
            )
            return

        self.state = replace(self.state, quote_currency=quote_currency)
        self._sync_buttons()
        content, chart_file = _build_price_message(snapshot)
        await interaction.response.edit_message(content=content, attachments=[chart_file], view=self)

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.message is None:
            return

        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            logger.debug("Failed to disable currency buttons after timeout.")


def _format_change_line(price_change_24h: float | None) -> str:
    if price_change_24h is None:
        return "24h: unavailable"

    sign = "+" if price_change_24h >= 0 else ""
    return f"24h: **{sign}{price_change_24h:.2f}%**"


def _build_price_message(snapshot: CryptoSnapshot) -> tuple[str, discord.File]:
    chart = render_price_chart(snapshot)
    filename = f"{snapshot.symbol.lower()}-{snapshot.vs_currency.lower()}-price.png"
    file = discord.File(chart, filename=filename)
    content = (
        f"**{snapshot.name} ({snapshot.symbol})**\n"
        f"Latest: **{format_price_label(snapshot.current_price, snapshot.vs_currency)}** | {_format_change_line(snapshot.price_change_24h)}\n"
        f"Quote: **{snapshot.vs_currency.upper()}** | Window: **{len(snapshot.points)} days**\n"
        "Use the buttons below to switch quote currency."
    )
    return content, file


def build_price_command(crypto_service: CoinGeckoCryptoService) -> app_commands.Command:
    @app_commands.command(
        name="price",
        description="Fetch the recent price trend for a cryptocurrency.",
    )
    @app_commands.describe(symbol="Crypto symbol such as BTC, ETH, SOL, XRP, ADA, or DOGE.")
    async def price(interaction: discord.Interaction, symbol: str) -> None:
        await interaction.response.defer(thinking=True)
        state = PriceRequestState(symbol=symbol.strip().upper(), quote_currency=DEFAULT_QUOTE_CURRENCY)

        try:
            snapshot = await crypto_service.get_snapshot(state.symbol, vs_currency=state.quote_currency)
        except (UnsupportedSymbolError, UnsupportedCurrencyError, MissingPriceDataError, CryptoServiceError) as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        except Exception:
            logger.exception("Unexpected failure while handling /price for %s", state.symbol)
            await interaction.followup.send(
                "Something went wrong while fetching crypto market data.",
                ephemeral=True,
            )
            return

        content, chart_file = _build_price_message(snapshot)
        view = PriceCurrencyView(crypto_service, state)
        sent_message = await interaction.followup.send(content=content, file=chart_file, view=view, wait=True)
        view.message = sent_message

    return price
