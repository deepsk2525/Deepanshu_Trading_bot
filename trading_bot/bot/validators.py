from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from .logging_config import get_logger

logger = get_logger("validators")

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


class ValidationError(ValueError):
    pass


def validate_symbol(symbol: str) -> str:
    if not symbol:
        raise ValidationError("Symbol must not be empty.")
    cleaned = symbol.strip().upper()
    if not cleaned.isalnum():
        raise ValidationError(
            f"Symbol '{cleaned}' must contain only letters and digits (e.g. BTCUSDT)."
        )
    logger.debug("Symbol validated: %s", cleaned)
    return cleaned


def validate_side(side: str) -> str:
    cleaned = side.strip().upper()
    if cleaned not in VALID_SIDES:
        raise ValidationError(
            f"Side '{cleaned}' is invalid. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    logger.debug("Side validated: %s", cleaned)
    return cleaned


def validate_order_type(order_type: str) -> str:
    cleaned = order_type.strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Order type '{cleaned}' is invalid. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    logger.debug("Order type validated: %s", cleaned)
    return cleaned


def validate_quantity(quantity: str | float) -> Decimal:
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValidationError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValidationError(f"Quantity must be greater than 0, got {qty}.")
    logger.debug("Quantity validated: %s", qty)
    return qty


def validate_price(price: Optional[str | float], order_type: str) -> Optional[Decimal]:
    order_type = order_type.strip().upper()

    if order_type == "MARKET":
        if price is not None:
            logger.warning("Price supplied for MARKET order – it will be ignored.")
        return None

    if price is None:
        raise ValidationError(f"Price is required for {order_type} orders.")
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValidationError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValidationError(f"Price must be greater than 0, got {p}.")
    logger.debug("Price validated: %s", p)
    return p


def validate_stop_price(
    stop_price: Optional[str | float], order_type: str
) -> Optional[Decimal]:
    order_type = order_type.strip().upper()

    if order_type != "STOP_MARKET":
        return None
    if stop_price is None:
        raise ValidationError("stopPrice is required for STOP_MARKET orders.")
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValidationError(f"stopPrice '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValidationError(f"stopPrice must be greater than 0, got {sp}.")
    logger.debug("Stop price validated: %s", sp)
    return sp


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
) -> dict:
    logger.debug(
        "Validating order params – symbol=%s side=%s type=%s qty=%s price=%s stop=%s",
        symbol, side, order_type, quantity, price, stop_price,
    )

    validated = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, order_type),
        "stop_price": validate_stop_price(stop_price, order_type),
    }

    logger.info(
        "Validation passed – %s %s %s qty=%s",
        validated["side"], validated["order_type"],
        validated["symbol"], validated["quantity"],
    )
    return validated
