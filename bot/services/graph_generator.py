from __future__ import annotations

from io import BytesIO
from typing import Callable

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from bot.services.crypto_service import CryptoSnapshot


def _format_price_label(value: float, currency: str) -> str:
    prefix = "$" if currency.lower() == "usd" else f"{currency.upper()} "
    absolute_value = abs(value)

    if absolute_value >= 1_000:
        return f"{prefix}{value:,.0f}"
    if absolute_value >= 1:
        return f"{prefix}{value:,.2f}"
    if absolute_value >= 0.01:
        return f"{prefix}{value:,.4f}"
    return f"{prefix}{value:,.6f}"


def _build_axis_formatter(currency: str) -> Callable[[float, int], str]:
    return lambda value, _: _format_price_label(value, currency)


def render_price_chart(snapshot: CryptoSnapshot) -> BytesIO:
    figure, axis = plt.subplots(figsize=(10, 5), constrained_layout=True)

    dates = [point.day for point in snapshot.points]
    values = [point.price for point in snapshot.points]

    axis.plot(dates, values, color="#0f766e", linewidth=2.4)
    axis.fill_between(dates, values, color="#14b8a6", alpha=0.18)

    axis.set_title(
        f"{snapshot.symbol} price trend ({snapshot.name})",
        fontsize=15,
        weight="bold",
    )
    axis.set_ylabel(f"Price in {snapshot.vs_currency.upper()}")
    axis.set_xlabel("Date")
    axis.grid(alpha=0.25)
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    axis.yaxis.set_major_formatter(FuncFormatter(_build_axis_formatter(snapshot.vs_currency)))
    axis.tick_params(axis="x", rotation=30)

    latest_point = snapshot.points[-1]
    axis.scatter([latest_point.day], [latest_point.price], color="#b91c1c", zorder=3)
    axis.annotate(
        _format_price_label(latest_point.price, snapshot.vs_currency),
        xy=(latest_point.day, latest_point.price),
        xytext=(10, 10),
        textcoords="offset points",
        fontsize=10,
        color="#b91c1c",
    )

    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=180)
    plt.close(figure)
    buffer.seek(0)
    return buffer
