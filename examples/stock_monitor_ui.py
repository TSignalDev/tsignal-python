# examples/07_stock_monitor_ui.py

"""
Stock monitor UI example.
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=no-member
# pylint: disable=unused-argument

import asyncio
from typing import Dict

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.clock import Clock

from utils import logger_setup
from stock_core import StockPrice, StockService, StockProcessor, StockViewModel
from tsignal import t_with_signals, t_slot

logger = logger_setup(__name__)


@t_with_signals
class StockView(BoxLayout):
    """Stock monitor UI view"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = 10
        self.padding = 10

        # Area to display status
        self.status_label = Label(
            text="Press Start to begin", size_hint_y=None, height=40
        )
        self.add_widget(self.status_label)

        # Start/Stop button
        self.control_button = Button(text="Start", size_hint_y=None, height=40)
        self.add_widget(self.control_button)

        # Stock selection (using only AAPL for now, expand as needed)
        self.stock_spinner = Spinner(
            text="AAPL",
            values=("AAPL",),
            size_hint_y=None,
            height=40,
        )
        self.add_widget(self.stock_spinner)

        # Display price
        self.price_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=40
        )
        self.price_label = Label(text="Price: --")
        self.change_label = Label(text="Change: --")
        self.price_layout.add_widget(self.price_label)
        self.price_layout.add_widget(self.change_label)
        self.add_widget(self.price_layout)

        # Alert setting layout
        self.alert_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=40, spacing=5
        )

        self.lower_input = TextInput(
            text="", hint_text="Lower", multiline=False, size_hint=(0.3, 1)
        )
        self.upper_input = TextInput(
            text="", hint_text="Upper", multiline=False, size_hint=(0.3, 1)
        )
        self.set_alert_button = Button(text="Set Alert", size_hint=(0.2, 1))
        self.remove_alert_button = Button(text="Remove Alert", size_hint=(0.2, 1))

        self.alert_layout.add_widget(self.lower_input)
        self.alert_layout.add_widget(self.upper_input)
        self.alert_layout.add_widget(self.set_alert_button)
        self.alert_layout.add_widget(self.remove_alert_button)

        self.add_widget(self.alert_layout)

        # Alert display label
        self.alert_label = Label(text="", size_hint_y=None, height=40)
        self.add_widget(self.alert_label)

        self.add_widget(Widget(size_hint_y=1))

    def update_prices(self, prices: Dict[str, StockPrice]):
        """Update price information"""

        if self.stock_spinner.text in prices:
            price_data = prices[self.stock_spinner.text]
            self.price_label.text = f"Price: {price_data.price:.2f}"
            self.change_label.text = f"Change: {price_data.change:+.2f}%"
            self.status_label.text = "Prices updated"

    @t_slot
    def on_alert_added(self, code: str, alert_type: str, price: float):
        """Update UI when alert is triggered"""
        self.alert_label.text = f"ALERT: {code} {alert_type} {price:.2f}"


class AsyncKivyApp(App):
    """Async Kivy app"""

    def __init__(self):
        super().__init__()
        self.background_task_running = True
        self.tasks = []
        self.view = None
        self.service = None
        self.processor = None
        self.viewmodel = None
        self.async_lib = None

    def build(self):
        """Build the UI"""

        self.view = StockView()

        self.service = StockService()
        self.processor = StockProcessor()
        self.viewmodel = StockViewModel()

        # Connect signals
        self.service.price_updated.connect(
            self.processor, self.processor.on_price_updated
        )
        self.processor.price_processed.connect(
            self.viewmodel, self.viewmodel.on_price_processed
        )
        self.viewmodel.prices_updated.connect(self.view, self.view.update_prices)

        # Alert related signals
        self.processor.alert_triggered.connect(
            self.viewmodel, self.viewmodel.on_alert_triggered
        )
        self.processor.alert_settings_changed.connect(
            self.viewmodel, self.viewmodel.on_alert_settings_changed
        )
        self.viewmodel.alert_added.connect(self.view, self.view.on_alert_added)

        # Alert setting/removal signals
        self.viewmodel.set_alert.connect(
            self.processor, self.processor.on_set_price_alert
        )
        self.viewmodel.remove_alert.connect(
            self.processor, self.processor.on_remove_price_alert
        )

        # Button event connections
        self.view.control_button.bind(on_press=self._toggle_service)
        self.view.set_alert_button.bind(on_press=self._set_alert)
        self.view.remove_alert_button.bind(on_press=self._remove_alert)

        Window.bind(on_request_close=self.on_request_close)

        return self.view

    def _toggle_service(self, instance):
        """Toggle service start/stop"""

        if instance.text == "Start":
            self.service.start()
            self.processor.start()
            instance.text = "Stop"
            self.view.status_label.text = "Service started"
        else:
            self.service.stop()
            self.processor.stop()
            instance.text = "Start"
            self.view.status_label.text = "Service stopped"

    def _set_alert(self, instance):
        """Alert setting button handler"""

        code = self.view.stock_spinner.text
        lower_str = self.view.lower_input.text.strip()
        upper_str = self.view.upper_input.text.strip()

        lower = float(lower_str) if lower_str else None
        upper = float(upper_str) if upper_str else None

        if not code:
            self.view.alert_label.text = "No stock selected"
            return

        self.viewmodel.set_alert.emit(code, lower, upper)
        self.view.alert_label.text = f"Alert set for {code}: lower={lower if lower else 'None'} upper={upper if upper else 'None'}"

    def _remove_alert(self, instance):
        """Alert removal button handler"""

        code = self.view.stock_spinner.text
        if not code:
            self.view.alert_label.text = "No stock selected"
            return

        self.viewmodel.remove_alert.emit(code)
        self.view.alert_label.text = f"Alert removed for {code}"

    async def background_task(self):
        """Background task"""

        try:
            while self.background_task_running:
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass

    def on_request_close(self, *args):
        """Request close handler"""

        asyncio.create_task(self.cleanup())
        return True

    async def cleanup(self):
        """Cleanup"""

        self.background_task_running = False
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.stop()

    async def async_run(self, async_lib=None):
        """Async run"""

        self._async_lib = async_lib or asyncio
        return await self._async_lib.gather(
            self._async_lib.create_task(super().async_run(async_lib=async_lib))
        )


async def main():
    """Main function"""

    Clock.init_async_lib("asyncio")

    app = AsyncKivyApp()
    background_task = asyncio.create_task(app.background_task())
    app.tasks.append(background_task)

    try:
        await app.async_run()
    except Exception as e:
        print(f"Error during app execution: {e}")
    finally:
        for task in app.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
