#!/usr/bin/env python3
"""
Main application entry point for the Weather Station Monitor.

This application:
1. Subscribes to MQTT weather data from localhost
2. Stores data in a SQLite database
3. Displays real-time data using GTK GUI (or console if GTK unavailable)

Usage:
    python main.py [--console] [--host HOST] [--port PORT] [--db DATABASE]

Arguments:
    --console     Force console mode even if GTK is available
    --host HOST   MQTT broker hostname (default: localhost)
    --port PORT   MQTT broker port (default: 1883)
    --db DATABASE Database file path (default: /deepsink1/weatherstation/data/weather_data.db)

NOTE: Daemon mode is DISABLED in development version.
      Production daemon runs via systemd service.
"""

import argparse
import sys
from weather_gui import WeatherGUI, SimpleWeatherDisplay, GTK_AVAILABLE
from weather_daemon import WeatherDaemon


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description="Weather Station Monitor (Development)")
    parser.add_argument("--console", action="store_true",
                        help="Force console mode even if GTK is available")
    parser.add_argument("--daemon", action="store_true",
                        help="DISABLED: Daemon mode runs via systemd service only")
    parser.add_argument("--host", default="localhost",
                        help="MQTT broker hostname (default: localhost)")
    parser.add_argument("--port", type=int, default=1883,
                        help="MQTT broker port (default: 1883)")
    parser.add_argument("--db", default="/deepsink1/weatherstation/data/weather_data.db",
                        help="Database file path (default: /deepsink1/weatherstation/data/weather_data.db)")
    parser.add_argument("--log", default="weather_daemon.log",
                        help="Log file path for daemon mode (default: weather_daemon.log)")
    parser.add_argument("--pid", default="weather_daemon.pid",
                        help="PID file path for daemon mode (default: weather_daemon.pid)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--silent", "-s", action="store_true",
                        help="Silent daemon mode - no console output, only file logging")

    args = parser.parse_args()

    # Daemon mode disabled in development version
    if args.daemon:
        print("\n" + "="*70)
        print("ERROR: Daemon mode is DISABLED in development version")
        print("="*70)
        print("\nThe weather station daemon runs as a systemd service in production.")
        print("\nTo manage the production daemon:")
        print("  sudo systemctl status weather-daemon   # Check status")
        print("  sudo systemctl restart weather-daemon  # Restart service")
        print("  sudo systemctl stop weather-daemon     # Stop service")
        print("\nTo view production logs:")
        print("  sudo journalctl -u weather-daemon -f")
        print("  tail -f /opt/weatherstation/logs/weather_daemon.log")
        print("\n" + "="*70)
        sys.exit(1)

    # Regular GUI/console modes
    print("Weather Station Monitor")
    print("======================")
    print(f"MQTT Broker: {args.host}:{args.port}")
    print(f"Database: {args.db}")

    # Determine which interface to use
    if args.console or not GTK_AVAILABLE:
        if args.console:
            print("Console mode requested")
        else:
            print("GTK not available, using console mode")
        print("Starting console interface...")
        app = SimpleWeatherDisplay()
    else:
        print("Starting GTK GUI...")
        app = WeatherGUI()

    try:
        app.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()