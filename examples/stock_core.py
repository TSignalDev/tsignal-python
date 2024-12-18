# examples/stock_core.py

# pylint: disable=no-member

"""
Stock monitoring core classes
"""

import asyncio
from dataclasses import dataclass
import logging
import random
import threading
import time
from typing import Dict, Optional
from tsignal import t_with_signals, t_signal, t_slot, t_with_worker

logger = logging.getLogger(__name__)


@dataclass
class StockPrice:
    """
    A dataclass to represent stock price data.
    """

    code: str
    price: float
    change: float
    timestamp: float


@t_with_worker
class StockService:
    """
    Virtual stock price data generator and distributor
    """

    def __init__(self):
        logger.debug("[StockService][__init__] started")

        self.prices: Dict[str, float] = {
            "AAPL": 180.0,  # Apple Inc.
            # "GOOGL": 140.0,  # Alphabet Inc.
            # "MSFT": 370.0,  # Microsoft Corporation
            # "AMZN": 145.0,  # Amazon.com Inc.
            # "TSLA": 240.0,  # Tesla Inc.
        }
        self._desc_lock = threading.RLock()
        self._descriptions = {
            "AAPL": "Apple Inc.",
            # "GOOGL": "Alphabet Inc.",
            # "MSFT": "Microsoft Corporation",
            # "AMZN": "Amazon.com Inc.",
            # "TSLA": "Tesla Inc.",
        }
        self.last_prices = self.prices.copy()
        self._running = False
        self._update_task = None
        self.started.connect(self.on_started)
        self.stopped.connect(self.on_stopped)
        super().__init__()

    @property
    def descriptions(self) -> Dict[str, str]:
        """Get the stock descriptions."""
        with self._desc_lock:
            return dict(self._descriptions)

    @t_signal
    def price_updated(self):
        """Signal emitted when stock price is updated"""

    async def on_started(self):
        """Worker initialization"""

        logger.info("[StockService][on_started] started")
        self._running = True
        self._update_task = asyncio.create_task(self.update_prices())

    async def on_stopped(self):
        """Worker shutdown"""

        logger.info("[StockService][on_stopped] stopped")
        self._running = False
        if hasattr(self, "_update_task"):
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

    async def update_prices(self):
        """Periodically update stock prices"""
        while self._running:
            for code, price in self.prices.items():
                self.last_prices[code] = price
                change_pct = random.uniform(-0.01, 0.01)
                self.prices[code] *= 1 + change_pct

                price_data = StockPrice(
                    code=code,
                    price=self.prices[code],
                    change=((self.prices[code] / self.last_prices[code]) - 1) * 100,
                    timestamp=time.time(),
                )
                logger.debug(
                    "[StockService][update_prices] price_data: %s",
                    price_data,
                )
                self.price_updated.emit(price_data)

            logger.debug(
                "[StockService][update_prices] prices updated price_data: %s",
                price_data,
            )

            await asyncio.sleep(1)


@t_with_signals
class StockViewModel:
    """
    UI state manager
    """

    def __init__(self):
        self.current_prices: Dict[str, StockPrice] = {}
        self.alerts: list[tuple[str, str, float]] = []
        self.alert_settings: Dict[str, tuple[Optional[float], Optional[float]]] = {}

    @t_signal
    def prices_updated(self):
        """Signal emitted when stock prices are updated"""

    @t_signal
    def alert_added(self):
        """Signal emitted when a new alert is added"""

    @t_signal
    def set_alert(self):
        """Signal emitted when user requests to set an alert"""

    @t_signal
    def remove_alert(self):
        """Signal emitted when user requests to remove an alert"""

    @t_slot
    def on_price_processed(self, price_data: StockPrice):
        """Receive processed stock price data from StockProcessor"""
        logger.debug("[StockViewModel][on_price_processed] price_data: %s", price_data)
        self.current_prices[price_data.code] = price_data
        self.prices_updated.emit(dict(self.current_prices))

    @t_slot
    def on_alert_triggered(self, code: str, alert_type: str, price: float):
        """Receive alert trigger from StockProcessor"""
        self.alerts.append((code, alert_type, price))
        self.alert_added.emit(code, alert_type, price)

    @t_slot
    def on_alert_settings_changed(
        self, code: str, lower: Optional[float], upper: Optional[float]
    ):
        """Receive alert settings change notification from StockProcessor"""
        if lower is None and upper is None:
            self.alert_settings.pop(code, None)
        else:
            self.alert_settings[code] = (lower, upper)


@t_with_worker
class StockProcessor:
    """
    Stock price data processor and alert condition checker
    """

    def __init__(self):
        logger.debug("[StockProcessor][__init__] started")
        self.price_alerts: Dict[str, tuple[Optional[float], Optional[float]]] = {}
        self.started.connect(self.on_started)
        self.stopped.connect(self.on_stopped)
        super().__init__()

    async def on_started(self):
        """Worker initialization"""

        logger.info("[StockProcessor][on_started] started")

    async def on_stopped(self):
        """Worker shutdown"""

        logger.info("[StockProcessor][on_stopped] stopped")

    @t_signal
    def price_processed(self):
        """Signal emitted when stock price is processed"""

    @t_signal
    def alert_triggered(self):
        """Signal emitted when price alert condition is met"""

    @t_signal
    def alert_settings_changed(self):
        """Signal emitted when price alert settings are changed"""

    @t_slot
    async def on_set_price_alert(
        self, code: str, lower: Optional[float], upper: Optional[float]
    ):
        """Receive price alert setting request from main thread"""
        self.price_alerts[code] = (lower, upper)
        self.alert_settings_changed.emit(code, lower, upper)

    @t_slot
    async def on_remove_price_alert(self, code: str):
        """Receive price alert removal request from main thread"""
        if code in self.price_alerts:
            del self.price_alerts[code]
            self.alert_settings_changed.emit(code, None, None)

    @t_slot
    async def on_price_updated(self, price_data: StockPrice):
        """Receive stock price update from StockService"""
        logger.debug("[StockProcessor][on_price_updated] price_data: %s", price_data)

        try:
            coro = self.process_price(price_data)
            self.queue_task(coro)
        except Exception as e:
            logger.error("[SLOT] Error in on_price_updated: %s", e, exc_info=True)

    async def process_price(self, price_data: StockPrice):
        """Process stock price data"""
        logger.debug("[StockProcessor][process_price] price_data: %s", price_data)
        try:
            if price_data.code in self.price_alerts:
                logger.debug(
                    "[process_price] Process price event loop: %s",
                    asyncio.get_running_loop(),
                )
            if price_data.code in self.price_alerts:
                lower, upper = self.price_alerts[price_data.code]
                if lower and price_data.price <= lower:
                    self.alert_triggered.emit(price_data.code, "LOW", price_data.price)
                if upper and price_data.price >= upper:
                    self.alert_triggered.emit(price_data.code, "HIGH", price_data.price)

            self.price_processed.emit(price_data)
        except Exception as e:
            logger.error("[StockProcessor][process_price] error: %s", e)
            raise
