from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Optional
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logging_config import get_logger

logger = get_logger("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10
RECV_WINDOW = 5_000


class BinanceAPIError(Exception):
    def __init__(self, code: int, message: str, http_status: int = 0):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"Binance API error {code}: {message}")


class BinanceNetworkError(Exception):
    pass


class BinanceFuturesClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or os.environ.get("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("BINANCE_API_SECRET", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "API key and secret are required. "
                "Pass them explicitly or set BINANCE_API_KEY / BINANCE_API_SECRET env vars."
            )

        self._session = self._build_session()
        logger.info("BinanceFuturesClient initialised (base_url=%s)", self.base_url)

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        signed: bool = True,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = {"X-MBX-APIKEY": self.api_key}
        payload = dict(params or {})

        if signed:
            payload = self._sign(payload)

        logger.debug(
            "-> %s %s  params=%s",
            method.upper(),
            endpoint,
            {k: v for k, v in payload.items() if k != "signature"},
        )

        try:
            if method.upper() in ("GET", "DELETE"):
                response = self._session.request(
                    method, url, params=payload, headers=headers, timeout=self.timeout
                )
            else:
                response = self._session.request(
                    method, url, data=payload, headers=headers, timeout=self.timeout
                )
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s %s", method, endpoint)
            raise BinanceNetworkError(f"Request timed out ({self.timeout}s)") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s", exc)
            raise BinanceNetworkError(f"Connection error: {exc}") from exc

        logger.debug("<- HTTP %s | %s", response.status_code, response.text[:500])

        try:
            data = response.json()
        except ValueError:
            logger.error(
                "Non-JSON response (HTTP %s): %s", response.status_code, response.text
            )
            raise BinanceAPIError(
                -1,
                f"Non-JSON response (HTTP {response.status_code})",
                response.status_code,
            )

        # Binance can return error payloads on 2xx (negative code = error)
        if isinstance(data, dict) and data.get("code", 0) < 0:
            logger.error(
                "API error code=%s msg=%s (HTTP %s)",
                data["code"], data.get("msg"), response.status_code,
            )
            raise BinanceAPIError(data["code"], data.get("msg", ""), response.status_code)

        if not response.ok:
            logger.error(
                "HTTP %s from %s: %s", response.status_code, endpoint, response.text[:300]
            )
            raise BinanceAPIError(
                response.status_code, response.text[:300], response.status_code
            )

        return data

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: Optional[str] = None,
        stop_price: Optional[str] = None,
        time_in_force: str = "GTC",
    ) -> dict:
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if order_type == "LIMIT":
            if not price:
                raise ValueError("Price is required for LIMIT orders.")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        if order_type == "STOP_MARKET":
            if not stop_price:
                raise ValueError("stopPrice is required for STOP_MARKET orders.")
            params["stopPrice"] = str(stop_price)

        logger.info(
            "Placing %s %s %s qty=%s price=%s stopPrice=%s",
            side, order_type, symbol, quantity, price, stop_price,
        )

        response = self._request("POST", "/fapi/v1/order", params=params)

        logger.info(
            "Order placed – orderId=%s status=%s executedQty=%s avgPrice=%s",
            response.get("orderId"), response.get("status"),
            response.get("executedQty"), response.get("avgPrice"),
        )

        return response

    def get_order(self, symbol: str, order_id: int) -> dict:
        return self._request(
            "GET", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id}
        )

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        logger.info("Cancelling orderId=%s on %s", order_id, symbol)
        return self._request(
            "DELETE", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id}
        )

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params)

    def get_account(self) -> dict:
        return self._request("GET", "/fapi/v2/account")

    def get_server_time(self) -> dict:
        return self._request("GET", "/fapi/v1/time", signed=False)
