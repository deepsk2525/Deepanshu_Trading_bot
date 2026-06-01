from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from .validators import validate_order_params, ValidationError
from .logging_config import get_logger

logger = get_logger("orders")


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[int] = None
    client_order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    orig_qty: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    price: Optional[str] = None
    raw: Optional[dict] = None
    error_message: Optional[str] = None

    def print_summary(self) -> None:
        sep = "─" * 55

        if not self.success:
            print(f"\n{'✗ ORDER FAILED':^55}")
            print(sep)
            print(f"  Error : {self.error_message}")
            print(sep)
            return

        print(f"\n{'✓ ORDER PLACED SUCCESSFULLY':^55}")
        print(sep)
        print(f"  Order ID       : {self.order_id}")
        print(f"  Client OID     : {self.client_order_id}")
        print(f"  Symbol         : {self.symbol}")
        print(f"  Side           : {self.side}")
        print(f"  Type           : {self.order_type}")
        print(f"  Status         : {self.status}")
        print(f"  Orig Qty       : {self.orig_qty}")
        print(f"  Executed Qty   : {self.executed_qty}")
        if self.avg_price and float(self.avg_price or 0) > 0:
            print(f"  Avg Price      : {self.avg_price}")
        if self.price and float(self.price or 0) > 0:
            print(f"  Limit Price    : {self.price}")
        print(sep)


class OrderService:
    def __init__(self, client: BinanceFuturesClient):
        self.client = client

    def place(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str | float,
        price: Optional[str | float] = None,
        stop_price: Optional[str | float] = None,
    ) -> OrderResult:
        try:
            params = validate_order_params(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
            )
        except ValidationError as exc:
            logger.warning("Validation failed: %s", exc)
            return OrderResult(success=False, error_message=str(exc))

        logger.info(
            "Order request – symbol=%s side=%s type=%s qty=%s price=%s stop=%s",
            params["symbol"], params["side"], params["order_type"],
            params["quantity"], params["price"], params["stop_price"],
        )
        self._print_request_summary(params)

        try:
            raw = self.client.place_order(
                symbol=str(params["symbol"]),
                side=str(params["side"]),
                order_type=str(params["order_type"]),
                quantity=str(params["quantity"]),
                price=str(params["price"]) if params["price"] else None,
                stop_price=str(params["stop_price"]) if params["stop_price"] else None,
            )
        except ValidationError as exc:
            logger.error("Validation error: %s", exc)
            return OrderResult(success=False, error_message=str(exc))
        except BinanceAPIError as exc:
            logger.error("Binance API error: code=%s msg=%s", exc.code, exc.message)
            return OrderResult(
                success=False,
                error_message=f"Binance API error [{exc.code}]: {exc.message}",
            )
        except BinanceNetworkError as exc:
            logger.error("Network error: %s", exc)
            return OrderResult(success=False, error_message=f"Network error: {exc}")

        result = OrderResult(
            success=True,
            order_id=raw.get("orderId"),
            client_order_id=raw.get("clientOrderId"),
            symbol=raw.get("symbol"),
            side=raw.get("side"),
            order_type=raw.get("type"),
            status=raw.get("status"),
            orig_qty=raw.get("origQty"),
            executed_qty=raw.get("executedQty"),
            avg_price=raw.get("avgPrice"),
            price=raw.get("price"),
            raw=raw,
        )

        logger.info(
            "Order response – orderId=%s status=%s executedQty=%s avgPrice=%s",
            result.order_id, result.status, result.executed_qty, result.avg_price,
        )

        return result

    @staticmethod
    def _print_request_summary(params: dict) -> None:
        sep = "─" * 55
        print(f"\n{'ORDER REQUEST SUMMARY':^55}")
        print(sep)
        print(f"  Symbol     : {params['symbol']}")
        print(f"  Side       : {params['side']}")
        print(f"  Type       : {params['order_type']}")
        print(f"  Quantity   : {params['quantity']}")
        if params.get("price"):
            print(f"  Price      : {params['price']}")
        if params.get("stop_price"):
            print(f"  Stop Price : {params['stop_price']}")
        print(sep)
