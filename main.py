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
    --db DATABASE Database file path (default: weather_data.db)
"""

import argparse
import sys
from weather_gui import WeatherGUI, SimpleWeatherDisplay, GTK_AVAILABLE
from weather_daemon import WeatherDaemon


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description="Weather Station Monitor")
    parser.add_argument("--console", action="store_true",
                        help="Force console mode even if GTK is available")
    parser.add_argument("--daemon", action="store_true",
                        help="Run in daemon mode (background, no display)")
    parser.add_argument("--host", default="localhost",
                        help="MQTT broker hostname (default: localhost)")
    parser.add_argument("--port", type=int, default=1883,
                        help="MQTT broker port (default: 1883)")
    parser.add_argument("--db", default="weather_data.db",
                        help="Database file path (default: weather_data.db)")
    parser.add_argument("--log", default="weather_daemon.log",
                        help="Log file path for daemon mode (default: weather_daemon.log)")
    parser.add_argument("--pid", default="weather_daemon.pid",
                        help="PID file path for daemon mode (default: weather_daemon.pid)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--silent", "-s", action="store_true",
                        help="Silent daemon mode - no console output, only file logging")

    args = parser.parse_args()

    # Handle daemon mode first
    if args.daemon:
        import logging
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        if not args.silent:
            print("Weather Station Monitor - Daemon Mode")
            print("====================================")
            print(f"MQTT Broker: {args.host}:{args.port}")
            print(f"Database: {args.db}")
            print(f"Log file: {args.log}")
            if args.silent:
                print("Silent mode - check log file for activity")
            else:
                print("Starting daemon mode (press Ctrl+C to stop)...")

        daemon = WeatherDaemon(args.host, args.port, args.db, args.log, args.silent, args.pid)
        try:
            daemon.start()
        except KeyboardInterrupt:
            print("\nDaemon interrupted by user")
            sys.exit(0)
        except Exception as e:
            print(f"Daemon error: {e}")
            sys.exit(1)
        return

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