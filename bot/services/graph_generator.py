from __future__ import annotations

from io import BytesIO
from typing import Callable

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.ticker import FuncFormatter, MaxNLocator

from bot.services.crypto_service import CryptoSnapshot

_PAGE_BACKGROUND = "#060816"
_PANEL_BACKGROUND = "#0B1220"
_GRID_COLOR = "#243142"
_TEXT_PRIMARY = "#F8FAFC"
_TEXT_SECONDARY = "#94A3B8"
_TEXT_MUTED = "#64748B"
_POSITIVE = "#22C55E"
_NEGATIVE = "#F43F5E"
_NEUTRAL = "#38BDF8"
_CURRENCY_PREFIXES = {
    "usd": "$",
    "eur": "EUR ",
    "jpy": "JPY ",
    "gbp": "GBP ",
}


def _blend_colors(base_color: str, target_color: str, weight: float) -> str:
    base_r, base_g, base_b = mcolors.to_rgb(base_color)
    target_r, target_g, target_b = mcolors.to_rgb(target_color)
    return mcolors.to_hex(
        (
            base_r + (target_r - base_r) * weight,
            base_g + (target_g - base_g) * weight,
            base_b + (target_b - base_b) * weight,
        )
    )


def _accent_color(snapshot: CryptoSnapshot) -> str:
    if snapshot.price_change_24h is None:
        return _NEUTRAL
    if snapshot.price_change_24h < 0:
        return _NEGATIVE
    return _POSITIVE


def format_price_label(value: float, currency: str) -> str:
    prefix = _CURRENCY_PREFIXES.get(currency.lower(), f"{currency.upper()} ")
    absolute_value = abs(value)

    if absolute_value >= 1_000:
        return f"{prefix}{value:,.0f}"
    if absolute_value >= 1:
        return f"{prefix}{value:,.2f}"
    if absolute_value >= 0.01:
        return f"{prefix}{value:,.4f}"
    return f"{prefix}{value:,.6f}"


def _build_axis_formatter(currency: str) -> Callable[[float, int], str]:
    return lambda value, _: format_price_label(value, currency)


def _draw_gradient_fill(axis: plt.Axes, dates: list, values: list[float], baseline: float, color: str) -> None:
    layers = 18
    for layer_index in range(layers):
        lower_ratio = layer_index / layers
        upper_ratio = (layer_index + 1) / layers
        lower_band = [baseline + (value - baseline) * lower_ratio for value in values]
        upper_band = [baseline + (value - baseline) * upper_ratio for value in values]
        alpha = 0.008 + (0.035 * (1 - lower_ratio) ** 1.7)
        axis.fill_between(dates, lower_band, upper_band, color=color, alpha=alpha, linewidth=0)


def _format_change_text(snapshot: CryptoSnapshot) -> tuple[str, str]:
    if snapshot.price_change_24h is None:
        return "24H CHANGE  N/A", _TEXT_SECONDARY

    sign = "+" if snapshot.price_change_24h >= 0 else ""
    color = _POSITIVE if snapshot.price_change_24h >= 0 else _NEGATIVE
    return f"24H CHANGE  {sign}{snapshot.price_change_24h:.2f}%", color


def render_price_chart(snapshot: CryptoSnapshot) -> BytesIO:
    figure, axis = plt.subplots(figsize=(11.5, 7.0), facecolor=_PAGE_BACKGROUND)
    figure.subplots_adjust(left=0.075, right=0.95, top=0.77, bottom=0.14)
    axis.set_facecolor(_PANEL_BACKGROUND)

    dates = [point.day for point in snapshot.points]
    values = [point.price for point in snapshot.points]
    accent_color = _accent_color(snapshot)
    glow_color = _blend_colors(accent_color, "#FFFFFF", 0.22)

    min_value = min(values)
    max_value = max(values)
    span = max_value - min_value
    padding = max(span * 0.28, max_value * 0.04 if max_value else 1.0)
    baseline = max(min_value - padding, 0) if min_value >= 0 else min_value - padding

    _draw_gradient_fill(axis, dates, values, baseline, accent_color)
    axis.plot(dates, values, color=glow_color, linewidth=10, alpha=0.06, solid_capstyle="round", zorder=3)
    axis.plot(dates, values, color=glow_color, linewidth=5.5, alpha=0.10, solid_capstyle="round", zorder=4)
    axis.plot(dates, values, color=accent_color, linewidth=2.8, solid_capstyle="round", zorder=5)

    latest_point = snapshot.points[-1]
    axis.scatter([latest_point.day], [latest_point.price], s=260, color=accent_color, alpha=0.14, zorder=6)
    axis.scatter([latest_point.day], [latest_point.price], s=110, color=accent_color, alpha=0.24, zorder=7)
    axis.scatter(
        [latest_point.day],
        [latest_point.price],
        s=34,
        color=_TEXT_PRIMARY,
        edgecolors=accent_color,
        linewidths=2.4,
        zorder=8,
    )

    axis.annotate(
        format_price_label(latest_point.price, snapshot.vs_currency),
        xy=(latest_point.day, latest_point.price),
        xytext=(-18, -16),
        textcoords="offset points",
        ha="right",
        fontsize=10,
        color=_TEXT_PRIMARY,
        bbox={
            "boxstyle": "round,pad=0.45",
            "facecolor": _blend_colors(_PANEL_BACKGROUND, accent_color, 0.12),
            "edgecolor": _blend_colors(accent_color, "#FFFFFF", 0.15),
            "linewidth": 1.0,
        },
        zorder=9,
    )

    axis.spines[:].set_visible(False)
    axis.yaxis.tick_right()
    axis.yaxis.set_label_position("right")
    axis.yaxis.set_major_formatter(FuncFormatter(_build_axis_formatter(snapshot.vs_currency)))
    axis.yaxis.set_major_locator(MaxNLocator(6))
    axis.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=6))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    axis.tick_params(axis="x", colors=_TEXT_SECONDARY, labelsize=10, length=0, pad=12)
    axis.tick_params(axis="y", colors=_TEXT_SECONDARY, labelsize=10, length=0, pad=12)
    axis.grid(axis="y", color=_GRID_COLOR, linewidth=0.8, alpha=0.6)
    axis.grid(axis="x", color=_GRID_COLOR, linewidth=0.6, alpha=0.22)
    axis.set_xlim(dates[0], dates[-1])
    axis.set_ylim(baseline, max_value + padding * 0.62)
    axis.margins(x=0.02)

    change_text, change_color = _format_change_text(snapshot)
    figure.text(0.08, 0.93, f"{snapshot.symbol}  |  {snapshot.name}", color=_TEXT_SECONDARY, fontsize=11, weight="bold")
    figure.text(0.08, 0.885, "LATEST PRICE", color=_TEXT_MUTED, fontsize=9, weight="bold")
    figure.text(0.08, 0.835, format_price_label(snapshot.current_price, snapshot.vs_currency), color=_TEXT_PRIMARY, fontsize=28, weight="bold")
    figure.text(
        0.08,
        0.79,
        change_text,
        color=change_color,
        fontsize=10,
        weight="bold",
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": _blend_colors(_PANEL_BACKGROUND, change_color, 0.10),
            "edgecolor": _blend_colors(change_color, "#FFFFFF", 0.18),
            "linewidth": 1.0,
        },
    )
    figure.text(0.95, 0.93, "MARKET SNAPSHOT", color=_TEXT_MUTED, fontsize=9, weight="bold", ha="right")
    figure.text(0.95, 0.885, snapshot.vs_currency.upper(), color=_TEXT_PRIMARY, fontsize=16, weight="bold", ha="right")
    figure.text(0.95, 0.845, f"{len(snapshot.points)}D HISTORY", color=_TEXT_SECONDARY, fontsize=10, ha="right")
    figure.text(0.08, 0.085, f"Source: {snapshot.source_name}", color=_TEXT_MUTED, fontsize=9)
    figure.text(0.95, 0.085, snapshot.source_url, color=_TEXT_MUTED, fontsize=8, ha="right")

    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=200, facecolor=figure.get_facecolor())
    plt.close(figure)
    buffer.seek(0)
    return buffer
