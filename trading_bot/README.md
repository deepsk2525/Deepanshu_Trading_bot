# Binance Futures Testnet Trading Bot

A Python CLI application for placing orders on the Binance USDT-M Futures Testnet. Supports `MARKET`, `LIMIT`, and `STOP_MARKET` orders with input validation, structured logging, and clean error handling.

Tested on Python 3.10+

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST client (HMAC signing, retries)
│   ├── orders.py          # Order placement logic + result formatting
│   ├── validators.py      # Input validation
│   └── logging_config.py  # Rotating file + console logger
├── cli.py                 # CLI entry point
├── logs/
│   └── trading_bot.log    # Auto-created on first run
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

## Setup

### 1. Get Testnet API credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Sign in with GitHub or Google
3. Go to **API Management → Generate Key**
4. Copy your **API Key** and **Secret Key**

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

Copy the example env file and fill in your keys:

```bash
cp .env .env
```

Edit `.env`:

```
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

The bot loads `.env` automatically on startup. You can also pass credentials directly as CLI flags if you prefer (see below).

---

## Running the Bot

All commands are run from inside the `trading_bot/` directory.

### Place a MARKET order

```bash
# BUY 0.001 BTC at market price
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# SELL 0.01 ETH at market price
python cli.py place --symbol ETHUSDT --side SELL --type MARKET --quantity 0.01
```

### Place a LIMIT order

```bash
# BUY 0.001 BTC with a limit price of 60000 USDT
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 60000

# SELL 0.05 ETH with a limit price of 3200 USDT
python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.05 --price 3200
```

### Place a STOP_MARKET order

```bash
# Trigger a market SELL of 0.001 BTC if price drops to 58000
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET \
    --quantity 0.001 --stop-price 58000
```

### View account balances

```bash
python cli.py account
```

### List open orders

```bash
python cli.py open-orders
python cli.py open-orders --symbol BTCUSDT
```

### Cancel an order

```bash
python cli.py cancel --symbol BTCUSDT --order-id 4020267671
```

### Pass credentials as flags (alternative to .env)

```bash
python cli.py --api-key YOUR_KEY --api-secret YOUR_SECRET place \
    --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

---

## Example Output

**MARKET BUY (fills immediately):**

```
       ORDER REQUEST SUMMARY
───────────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
───────────────────────────────────────────────────────

       ✓ ORDER PLACED SUCCESSFULLY
───────────────────────────────────────────────────────
  Order ID       : 4020267671
  Client OID     : ios7AhKXtEUb1DkxAtDqzS
  Symbol         : BTCUSDT
  Side           : BUY
  Type           : MARKET
  Status         : FILLED
  Orig Qty       : 0.001
  Executed Qty   : 0.001
  Avg Price      : 67284.50
───────────────────────────────────────────────────────
```

**LIMIT SELL (sits open until price is reached):**

```
  Status         : NEW
  Executed Qty   : 0.000
  Limit Price    : 3200.00
```

**Validation failure:**

```
✗ ORDER FAILED
───────────────────────────────────────────────────────
  Error : Price is required for LIMIT orders.
───────────────────────────────────────────────────────
```

---

## Logging

Logs are written to `logs/trading_bot.log` and rotate at 5 MB (3 backups kept).

- **File**: DEBUG level — full request/response audit trail
- **Console**: WARNING and above — only errors shown in terminal

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing credentials | Clear message, exits with code 2 |
| Invalid symbol / side / type | ValidationError shown, nothing sent to API |
| Negative or zero quantity | ValidationError shown |
| Missing price for LIMIT | ValidationError shown |
| Binance API error (e.g. -1121) | Error code + message displayed |
| Network timeout | Retried up to 3×, then friendly error message |

---

## Assumptions

- Targets the USDT-M Futures Testnet only. The `--base-url` flag allows switching to mainnet.
- `timeInForce` defaults to `GTC` for LIMIT orders.
- Quantity/price precision is not auto-adjusted — values must conform to the symbol's rules on the testnet. If an order is rejected for precision, check `/fapi/v1/exchangeInfo` for the symbol's `stepSize` and `tickSize`.
