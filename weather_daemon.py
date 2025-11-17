"""
Daemon mode for weather station data collection.
Runs in background with no display, only database updates.
"""

import logging
import logging.handlers
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict

from database import WeatherDatabase
from mqtt_subscriber import WeatherMQTTSubscriber


class WeatherDaemon:
    """Daemon for background weather data collection."""

    def __init__(self, host: str = "localhost", port: int = 1883, db_path: str = "/deepsink1/weatherstation/data/weather_data.db",
                 log_file: str = "weather_daemon.log", silent: bool = False, pid_file: str = "weather_daemon.pid"):
        self.host = host
        self.port = port
        self.db_path = db_path
        self.log_file = log_file
        self.pid_file = pid_file
        self.silent = silent
        self.running = False

        # Set up logging
        self.setup_logging(silent)

        # Initialize components
        self.database = WeatherDatabase(db_path)
        self.mqtt_subscriber = WeatherMQTTSubscriber(host, port, db_path)
        self.mqtt_subscriber.set_data_callback(self.on_data_received)

        # Statistics tracking
        self.start_time = None
        self.weather_messages = 0
        self.flux_messages = 0
        self.last_weather_time = None
        self.last_flux_time = None

        # Set up signal handlers for graceful shutdown and log rotation
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGUSR1, self.reopen_log_file)  # For log rotation

    def setup_logging(self, silent: bool = False):
        """Configure logging for daemon mode."""
        handlers = [logging.FileHandler(self.log_file)]

        # Add console output unless silent mode is requested
        if not silent:
            handlers.append(logging.StreamHandler(sys.stdout))

        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        self.logger = logging.getLogger(__name__)

    def on_data_received(self, topic: str, data: Dict):
        """Callback for when new MQTT data arrives."""
        current_time = datetime.now()

        if "weathermeters" in topic:
            self.weather_messages += 1
            self.last_weather_time = current_time
            self.logger.info(f"Weather data received: temp={data.get('temperature', 'N/A')}°C, "
                           f"humidity={data.get('humidity', 'N/A')}%, "
                           f"pressure={data.get('pressure', 'N/A')}hPa")
        elif "magneticfluxsensor" in topic:
            self.flux_messages += 1
            self.last_flux_time = current_time
            self.logger.debug(f"Magnetic flux data received: x={data.get('x')}, "
                            f"y={data.get('y')}, z={data.get('z')}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def reopen_log_file(self, signum, frame):
        """Handle USR1 signal to reopen log file for rotation."""
        self.logger.info("Received USR1 signal, reopening log file...")

        # Close existing handlers
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

        # Recreate logging setup
        self.setup_logging(self.silent)
        self.logger.info("Log file reopened successfully")

    def log_statistics(self):
        """Log daemon statistics."""
        if self.start_time:
            uptime = datetime.now() - self.start_time
            self.logger.info(f"Daemon statistics - Uptime: {uptime}, "
                           f"Weather messages: {self.weather_messages}, "
                           f"Flux messages: {self.flux_messages}")

            if self.last_weather_time:
                time_since_weather = datetime.now() - self.last_weather_time
                self.logger.info(f"Last weather data: {time_since_weather.total_seconds():.0f} seconds ago")

            if self.last_flux_time:
                time_since_flux = datetime.now() - self.last_flux_time
                self.logger.debug(f"Last flux data: {time_since_flux.total_seconds():.0f} seconds ago")

    def write_pid_file(self):
        """Write the current process ID to a PID file."""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            self.logger.info(f"PID file written: {self.pid_file}")
        except Exception as e:
            self.logger.warning(f"Failed to write PID file: {e}")

    def remove_pid_file(self):
        """Remove the PID file."""
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                self.logger.info(f"PID file removed: {self.pid_file}")
        except Exception as e:
            self.logger.warning(f"Failed to remove PID file: {e}")

    def start(self):
        """Start the daemon."""
        self.logger.info("Starting Weather Station Daemon")
        self.logger.info(f"MQTT Broker: {self.host}:{self.port}")
        self.logger.info(f"Database: {self.db_path}")
        self.logger.info(f"Log file: {self.log_file}")
        self.logger.info(f"PID file: {self.pid_file}")

        try:
            # Write PID file
            self.write_pid_file()

            # Start MQTT subscriber
            self.mqtt_subscriber.start()
            self.running = True
            self.start_time = datetime.now()

            self.logger.info("Daemon started successfully")

            # Main daemon loop
            stats_counter = 0
            while self.running:
                time.sleep(1)

                # Log statistics every 5 minutes (300 seconds)
                stats_counter += 1
                if stats_counter >= 300:
                    self.log_statistics()
                    stats_counter = 0

                # Check if MQTT connection is still alive
                if not self.mqtt_subscriber.is_connected():
                    self.logger.warning("MQTT connection lost, attempting to reconnect...")
                    try:
                        self.mqtt_subscriber.start()
                    except Exception as e:
                        self.logger.error(f"Reconnection failed: {e}")
                        time.sleep(10)  # Wait before next reconnection attempt

        except KeyboardInterrupt:
            self.logger.info("Daemon interrupted by user")
        except Exception as e:
            self.logger.error(f"Daemon error: {e}")
            raise
        finally:
            self.stop()

    def stop(self):
        """Stop the daemon."""
        if self.running:
            self.logger.info("Stopping Weather Station Daemon")
            self.running = False

            # Stop MQTT subscriber
            if self.mqtt_subscriber:
                self.mqtt_subscriber.stop()

            # Log final statistics
            self.log_statistics()

            # Remove PID file
            self.remove_pid_file()

            self.logger.info("Daemon stopped")


    def status(self):
        """Get daemon status information."""
        status_info = {
            'running': self.running,
            'start_time': self.start_time,
            'weather_messages': self.weather_messages,
            'flux_messages': self.flux_messages,
            'last_weather_time': self.last_weather_time,
            'last_flux_time': self.last_flux_time,
            'mqtt_connected': self.mqtt_subscriber.is_connected() if self.mqtt_subscriber else False
        }
        return status_info


def main():
    """Main function for daemon mode."""
    import argparse

    parser = argparse.ArgumentParser(description="Weather Station Daemon")
    parser.add_argument("--host", default="localhost",
                        help="MQTT broker hostname (default: localhost)")
    parser.add_argument("--port", type=int, default=1883,
                        help="MQTT broker port (default: 1883)")
    parser.add_argument("--db", default="/deepsink1/weatherstation/data/weather_data.db",
                        help="Database file path (default: /deepsink1/weatherstation/data/weather_data.db)")
    parser.add_argument("--log", default="weather_daemon.log",
                        help="Log file path (default: weather_daemon.log)")
    parser.add_argument("--pid", default="weather_daemon.pid",
                        help="PID file path (default: weather_daemon.pid)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--silent", "-s", action="store_true",
                        help="Silent mode - no console output, only file logging")

    args = parser.parse_args()

    # Adjust log level if verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create and start daemon
    daemon = WeatherDaemon(args.host, args.port, args.db, args.log, args.silent, args.pid)

    try:
        daemon.start()
    except Exception as e:
        print(f"Failed to start daemon: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()