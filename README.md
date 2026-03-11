# Python Discord Crypto Bot

This project now provides a crypto-focused `/price` slash command for Discord.

## What it does

- Accepts `/price symbol:<CODE>`
- Fetches current crypto prices and recent price history from CoinGecko
- Generates a PNG line chart with matplotlib
- Sends the chart back to the same Discord channel
- Handles unsupported symbols and missing history with clear error messages

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
- CoinGecko symbol matching is market-based, so the command picks the highest market-cap asset for the exact symbol match.
- `COINGECKO_API_KEY` is optional for this first implementation, but the config already supports it.
- The structure is ready for future scraper-based commands under `bot/commands` and `bot/services`.
