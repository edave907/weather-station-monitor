"""
GTK GUI for real-time weather station data display.
Note: Requires PyGObject to be installed with system dependencies.
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib
    GTK_AVAILABLE = True
except ImportError:
    print("GTK not available. Install system dependencies:")
    print("sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0")
    print("pip install PyGObject")
    GTK_AVAILABLE = False

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

from database import WeatherDatabase
from mqtt_subscriber import WeatherMQTTSubscriber


class WeatherGUI:
    """GTK GUI for weather station data display."""

    def __init__(self):
        if not GTK_AVAILABLE:
            raise ImportError("GTK is not available")

        self.database = WeatherDatabase()
        self.mqtt_subscriber = WeatherMQTTSubscriber()

        # Set up MQTT callback for real-time updates
        self.mqtt_subscriber.set_data_callback(self.on_new_data)

        self.window = None
        self.labels = {}
        self.update_running = True

        self.setup_gui()

    def setup_gui(self):
        """Set up the GTK GUI."""
        self.window = Gtk.Window(title="Weather Station Monitor")
        self.window.set_default_size(800, 600)
        self.window.connect("destroy", self.on_destroy)

        # Create main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_left(10)
        main_box.set_margin_right(10)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        self.window.add(main_box)

        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<big><b>Weather Station Monitor</b></big>")
        main_box.pack_start(title_label, False, False, 0)

        # Current weather frame
        current_frame = Gtk.Frame(label="Current Weather")
        current_box = Gtk.Grid()
        current_box.set_margin_left(10)
        current_box.set_margin_right(10)
        current_box.set_margin_top(10)
        current_box.set_margin_bottom(10)
        current_box.set_row_spacing(5)
        current_box.set_column_spacing(10)
        current_frame.add(current_box)
        main_box.pack_start(current_frame, False, False, 0)

        # Create labels for current weather data
        weather_fields = [
            ("Temperature", "°C"),
            ("Humidity", "%"),
            ("Pressure", "hPa"),
            ("Irradiance", ""),
            ("Wind Direction", ""),
            ("Rain Gauge", "count"),
            ("Anemometer", "count"),
            ("Last Updated", "")
        ]

        for i, (field, unit) in enumerate(weather_fields):
            label = Gtk.Label(f"{field}:")
            label.set_alignment(0, 0.5)
            current_box.attach(label, 0, i, 1, 1)

            value_label = Gtk.Label("--")
            value_label.set_alignment(0, 0.5)
            current_box.attach(value_label, 1, i, 1, 1)

            if unit:
                unit_label = Gtk.Label(unit)
                unit_label.set_alignment(0, 0.5)
                current_box.attach(unit_label, 2, i, 1, 1)

            self.labels[field.lower().replace(" ", "_")] = value_label

        # Connection status
        status_frame = Gtk.Frame(label="Connection Status")
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        status_box.set_margin_left(10)
        status_box.set_margin_right(10)
        status_box.set_margin_top(10)
        status_box.set_margin_bottom(10)
        status_frame.add(status_box)
        main_box.pack_start(status_frame, False, False, 0)

        status_box.pack_start(Gtk.Label("MQTT Status:"), False, False, 0)
        self.mqtt_status_label = Gtk.Label("Disconnected")
        status_box.pack_start(self.mqtt_status_label, False, False, 0)

        # Control buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        main_box.pack_start(button_box, False, False, 0)

        connect_button = Gtk.Button(label="Connect MQTT")
        connect_button.connect("clicked", self.on_connect_clicked)
        button_box.pack_start(connect_button, False, False, 0)

        disconnect_button = Gtk.Button(label="Disconnect MQTT")
        disconnect_button.connect("clicked", self.on_disconnect_clicked)
        button_box.pack_start(disconnect_button, False, False, 0)

        refresh_button = Gtk.Button(label="Refresh Data")
        refresh_button.connect("clicked", self.on_refresh_clicked)
        button_box.pack_start(refresh_button, False, False, 0)

    def on_new_data(self, topic: str, data: Dict):
        """Callback for when new MQTT data arrives."""
        if "weathermeters" in topic:
            # Schedule GUI update in main thread
            GLib.idle_add(self.update_weather_display)

    def update_weather_display(self):
        """Update the weather display with latest data from database."""
        summary = self.database.get_current_weather_summary()
        if summary:
            self.labels["temperature"].set_text(f"{summary.get('temperature', '--'):.1f}" if summary.get('temperature') else "--")
            self.labels["humidity"].set_text(f"{summary.get('humidity', '--'):.1f}" if summary.get('humidity') else "--")
            self.labels["pressure"].set_text(f"{summary.get('pressure', '--'):.1f}" if summary.get('pressure') else "--")
            self.labels["irradiance"].set_text(f"{summary.get('irradiance', '--'):.3f}" if summary.get('irradiance') else "--")
            self.labels["wind_direction"].set_text(str(summary.get('wind_direction', '--')))
            self.labels["rain_gauge"].set_text(str(summary.get('rain_gauge_count', '--')))
            self.labels["anemometer"].set_text(str(summary.get('anemometer_count', '--')))

            if summary.get('last_updated'):
                self.labels["last_updated"].set_text(summary['last_updated'])

    def update_mqtt_status(self):
        """Update MQTT connection status display."""
        if self.mqtt_subscriber.is_connected():
            self.mqtt_status_label.set_markup('<span color="green">Connected</span>')
        else:
            self.mqtt_status_label.set_markup('<span color="red">Disconnected</span>')

    def on_connect_clicked(self, button):
        """Handle connect button click."""
        try:
            self.mqtt_subscriber.start()
            GLib.timeout_add(1000, self.update_status_periodically)
        except Exception as e:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=f"Failed to connect to MQTT broker: {e}"
            )
            dialog.run()
            dialog.destroy()

    def on_disconnect_clicked(self, button):
        """Handle disconnect button click."""
        self.mqtt_subscriber.stop()
        self.update_mqtt_status()

    def on_refresh_clicked(self, button):
        """Handle refresh button click."""
        self.update_weather_display()

    def update_status_periodically(self):
        """Periodically update the connection status."""
        if self.update_running:
            self.update_mqtt_status()
            return True  # Continue the timeout
        return False  # Stop the timeout

    def on_destroy(self, widget):
        """Handle window destroy event."""
        self.update_running = False
        self.mqtt_subscriber.stop()
        Gtk.main_quit()

    def run(self):
        """Run the GUI application."""
        self.window.show_all()

        # Start periodic updates
        GLib.timeout_add(1000, self.update_status_periodically)
        GLib.timeout_add(5000, self.update_weather_display)  # Update every 5 seconds

        Gtk.main()


class SimpleWeatherDisplay:
    """Simple console-based weather display when GTK is not available."""

    def __init__(self):
        self.database = WeatherDatabase()
        self.mqtt_subscriber = WeatherMQTTSubscriber()
        self.mqtt_subscriber.set_data_callback(self.on_new_data)
        self.running = False

    def on_new_data(self, topic: str, data: Dict):
        """Callback for when new MQTT data arrives."""
        if "weathermeters" in topic:
            self.display_current_weather()

    def display_current_weather(self):
        """Display current weather data in console."""
        summary = self.database.get_current_weather_summary()
        if summary:
            print("\n" + "="*50)
            print("CURRENT WEATHER DATA")
            print("="*50)
            print(f"Temperature:    {summary.get('temperature', 'N/A'):.1f} °C" if summary.get('temperature') else "Temperature:    N/A")
            print(f"Humidity:       {summary.get('humidity', 'N/A'):.1f} %" if summary.get('humidity') else "Humidity:       N/A")
            print(f"Pressure:       {summary.get('pressure', 'N/A'):.1f} hPa" if summary.get('pressure') else "Pressure:       N/A")
            print(f"Irradiance:     {summary.get('irradiance', 'N/A'):.3f}" if summary.get('irradiance') else "Irradiance:     N/A")
            print(f"Wind Direction: {summary.get('wind_direction', 'N/A')}")
            print(f"Rain Gauge:     {summary.get('rain_gauge_count', 'N/A')}")
            print(f"Anemometer:     {summary.get('anemometer_count', 'N/A')}")
            print(f"Last Updated:   {summary.get('last_updated', 'N/A')}")
            print("="*50)

    def run(self):
        """Run the simple display."""
        print("Starting weather monitor...")
        print("GTK GUI not available, using console display.")
        print("Press Ctrl+C to stop.\n")

        try:
            self.mqtt_subscriber.start()
            self.running = True

            # Display initial data
            self.display_current_weather()

            # Keep running and display updates
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nShutting down...")
            self.mqtt_subscriber.stop()


def main():
    """Main function to run the weather display."""
    if GTK_AVAILABLE:
        app = WeatherGUI()
        app.run()
    else:
        app = SimpleWeatherDisplay()
        app.run()


if __name__ == "__main__":
    main()