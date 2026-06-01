#!/usr/bin/env python3
import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from bot.logging_config import setup_logging, get_logger
from bot.orders import OrderService

setup_logging("DEBUG")
logger = get_logger("cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet – order placement CLI",
    )
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--api-secret", default=None)
    parser.add_argument(
        "--base-url",
        default="https://testnet.binancefuture.com",
        help="Override the base URL (default: testnet)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # place
    place = sub.add_parser("place", help="Place a new order")
    place.add_argument("--symbol", "-s", required=True)
    place.add_argument("--side", required=True, choices=["BUY", "SELL"], type=str.upper)
    place.add_argument(
        "--type", "-t",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        type=str.upper,
    )
    place.add_argument("--quantity", "-q", required=True)
    place.add_argument("--price", "-p", default=None)
    place.add_argument("--stop-price", dest="stop_price", default=None)

    # account
    sub.add_parser("account", help="Show account balances")

    # open-orders
    oo = sub.add_parser("open-orders", help="List open orders")
    oo.add_argument("--symbol", "-s", default=None)

    # cancel
    cancel = sub.add_parser("cancel", help="Cancel an order by ID")
    cancel.add_argument("--symbol", "-s", required=True)
    cancel.add_argument("--order-id", required=True, type=int)

    return parser


def cmd_place(args, client: BinanceFuturesClient) -> int:
    result = OrderService(client).place(
        symbol=args.symbol,
        side=args.side,
        order_type=args.order_type,
        quantity=args.quantity,
        price=args.price,
        stop_price=args.stop_price,
    )
    result.print_summary()
    return 0 if result.success else 1


def cmd_account(args, client: BinanceFuturesClient) -> int:
    print("\nFetching account information...")
    try:
        account = client.get_account()
    except (BinanceAPIError, BinanceNetworkError) as exc:
        print(f"\n✗ Failed to fetch account: {exc}")
        logger.error("account fetch failed: %s", exc)
        return 1

    sep = "─" * 55
    print(f"\n{'ACCOUNT BALANCES':^55}")
    print(sep)
    assets = [a for a in account.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    if assets:
        for a in assets:
            print(
                f"  {a['asset']:<10}  wallet={float(a['walletBalance']):.4f}"
                f"  available={float(a['availableBalance']):.4f}"
            )
    else:
        print("  (no non-zero balances)")
    print(sep)
    return 0


def cmd_open_orders(args, client: BinanceFuturesClient) -> int:
    sym = getattr(args, "symbol", None)
    print(f"\nFetching open orders{' for ' + sym if sym else ''}...")
    try:
        orders = client.get_open_orders(symbol=sym)
    except (BinanceAPIError, BinanceNetworkError) as exc:
        print(f"\n✗ Failed to fetch open orders: {exc}")
        logger.error("open-orders fetch failed: %s", exc)
        return 1

    sep = "─" * 70
    print(f"\n{'OPEN ORDERS':^70}")
    print(sep)
    if not orders:
        print("  No open orders.")
    for o in orders:
        print(
            f"  [{o['orderId']}] {o['symbol']} {o['side']} {o['type']}"
            f"  qty={o['origQty']}  price={o['price']}  status={o['status']}"
        )
    print(sep)
    return 0


def cmd_cancel(args, client: BinanceFuturesClient) -> int:
    print(f"\nCancelling order {args.order_id} on {args.symbol}...")
    try:
        resp = client.cancel_order(symbol=args.symbol, order_id=args.order_id)
    except (BinanceAPIError, BinanceNetworkError) as exc:
        print(f"\n✗ Failed to cancel order: {exc}")
        logger.error("cancel failed: %s", exc)
        return 1
    print(f"\n✓ Order cancelled – status={resp.get('status')}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logger.info("CLI invoked – command=%s", args.command)

    api_key = args.api_key or os.environ.get("BINANCE_API_KEY")
    api_secret = args.api_secret or os.environ.get("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        print(
            "\n✗ API credentials are required.\n"
            "  Copy .env.example to .env and fill in your testnet credentials,\n"
            "  or pass --api-key / --api-secret flags.\n"
        )
        return 2

    try:
        client = BinanceFuturesClient(
            api_key=api_key,
            api_secret=api_secret,
            base_url=args.base_url,
        )
    except ValueError as exc:
        print(f"\n✗ {exc}")
        return 2

    handlers = {
        "place": cmd_place,
        "account": cmd_account,
        "open-orders": cmd_open_orders,
        "cancel": cmd_cancel,
    }

    try:
        return handlers[args.command](args, client)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        print(f"\n✗ Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
