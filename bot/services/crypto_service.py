from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import aiohttp


@dataclass(frozen=True)
class PricePoint:
    day: date
    price: float


@dataclass(frozen=True)
class CryptoSnapshot:
    symbol: str
    name: str
    coin_id: str
    vs_currency: str
    current_price: float
    points: list[PricePoint]
    price_change_24h: float | None
    source_name: str
    source_url: str


class CryptoServiceError(RuntimeError):
    pass


class UnsupportedSymbolError(CryptoServiceError):
    pass


class MissingPriceDataError(CryptoServiceError):
    pass


class CoinGeckoCryptoService:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        vs_currency: str,
        history_days: int,
        api_key: str | None = None,
    ) -> None:
        self.session = session
        self.vs_currency = vs_currency.lower()
        self.history_days = history_days
        self.api_key = api_key
        self.base_url = "https://api.coingecko.com/api/v3"

    async def _get_json(self, path: str, params: dict[str, Any]) -> Any:
        headers = {
            "Accept": "application/json",
            "User-Agent": "python-discord-scraper/1.0",
        }
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key

        async with self.session.get(
            f"{self.base_url}{path}",
            params=params,
            headers=headers,
        ) as response:
            if response.status == 429:
                raise CryptoServiceError("CoinGecko rate limit reached. Please try again in a moment.")
            if response.status >= 400:
                details = (await response.text()).strip()
                message = details or f"HTTP {response.status}"
                raise CryptoServiceError(f"CoinGecko request failed: {message}")
            return await response.json()

    async def _lookup_asset(self, symbol: str) -> dict[str, Any]:
        markets = await self._get_json(
            "/coins/markets",
            {
                "vs_currency": self.vs_currency,
                "symbols": symbol,
                "include_tokens": "top",
                "order": "market_cap_desc",
                "per_page": 10,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h",
                "precision": "full",
            },
        )

        if not isinstance(markets, list):
            raise CryptoServiceError("CoinGecko returned an unexpected asset lookup response.")

        normalized_symbol = symbol.lower()
        for asset in markets:
            if str(asset.get("symbol", "")).lower() == normalized_symbol:
                return asset

        raise UnsupportedSymbolError(
            f"Unsupported crypto symbol '{symbol.upper()}'. Try symbols like BTC, ETH, SOL, XRP, ADA, or DOGE."
        )

    def _normalize_points(self, raw_prices: list[list[float]]) -> list[PricePoint]:
        daily_points: dict[date, float] = {}
        for item in raw_prices:
            if len(item) < 2:
                continue

            timestamp_ms, price = item[0], item[1]
            if price is None:
                continue

            point_day = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).date()
            daily_points[point_day] = float(price)

        points = [PricePoint(day=point_day, price=price) for point_day, price in sorted(daily_points.items())]
        return points[-self.history_days :]

    async def get_snapshot(self, symbol: str) -> CryptoSnapshot:
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol or not normalized_symbol.replace("-", "").isalnum():
            raise UnsupportedSymbolError("Please provide a valid crypto symbol such as BTC, ETH, SOL, XRP, ADA, or DOGE.")

        asset = await self._lookup_asset(normalized_symbol)
        coin_id = str(asset.get("id", "")).strip()
        name = str(asset.get("name", normalized_symbol)).strip() or normalized_symbol
        current_price = asset.get("current_price")

        history = await self._get_json(
            f"/coins/{coin_id}/market_chart",
            {
                "vs_currency": self.vs_currency,
                "days": self.history_days,
                "interval": "daily",
                "precision": "full",
            },
        )

        raw_prices = history.get("prices", []) if isinstance(history, dict) else []
        points = self._normalize_points(raw_prices)
        if not points:
            raise MissingPriceDataError(f"CoinGecko returned no recent price history for {normalized_symbol}.")

        resolved_current_price = float(current_price) if current_price is not None else points[-1].price
        price_change_24h = asset.get("price_change_percentage_24h")
        if price_change_24h is None:
            price_change_24h = asset.get("price_change_percentage_24h_in_currency")

        return CryptoSnapshot(
            symbol=normalized_symbol,
            name=name,
            coin_id=coin_id,
            vs_currency=self.vs_currency,
            current_price=resolved_current_price,
            points=points,
            price_change_24h=float(price_change_24h) if price_change_24h is not None else None,
            source_name="CoinGecko API",
            source_url=f"https://www.coingecko.com/en/coins/{coin_id}",
        )
