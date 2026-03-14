# Python Discord Crypto Bot

This project provides a crypto-focused `/price` slash command for Discord with a dark, market-style chart and quote-currency switch buttons.

## What it does

- Accepts `/price symbol:<CODE>`
- Fetches current crypto prices and recent price history from CoinGecko
- Generates a premium dark-theme PNG chart with matplotlib
- Sends the chart back to the same Discord channel
- Adds Discord buttons for `USD`, `EUR`, `JPY`, and `GBP`
- Re-renders the same symbol in the selected quote currency when a button is clicked
- Handles unsupported symbols, currencies, and missing history with clear error messages

## Project structure

```text
main.py
bot/
  bot.py
  commands/
    price.py
  services/
    crypto_service.py
    graph_generator.py
  utils/
    config.py
```

## Setup

1. Activate the virtual environment.
2. Install dependencies:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Configure `.env`:

```env
BOT_TOKEN=your-discord-bot-token
CRYPTO_VS_CURRENCY=usd
CRYPTO_HISTORY_DAYS=30
COINGECKO_API_KEY=
```

4. Start the bot:

```powershell
venv\Scripts\python.exe main.py
```

## Notes

- `/price` expects symbols like `BTC`, `ETH`, `SOL`, `XRP`, `ADA`, or `DOGE`.
- The chart defaults to `USD` and can be switched to `EUR`, `JPY`, or `GBP` with Discord buttons.
- CoinGecko symbol matching is market-based, so the command picks the highest market-cap asset for the exact symbol match.
- `COINGECKO_API_KEY` is optional for this implementation, but the config already supports it.
- The command/view structure is ready for future additions like timeframe buttons.
