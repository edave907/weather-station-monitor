"""
MQTT subscriber for weather station data collection.
"""
import json
import logging
import threading
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from database import WeatherDatabase


class WeatherMQTTSubscriber:
    """MQTT subscriber for weather station data."""

    def __init__(self, host: str = "localhost", port: int = 1883, db_path: str = "/deepsink1/weatherstation/data/weather_data.db"):
        self.host = host
        self.port = port
        self.client = mqtt.Client()
        self.database = WeatherDatabase(db_path)
        self.running = False
        self.data_callback: Optional[Callable] = None

        # Configure MQTT client
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def set_data_callback(self, callback: Callable) -> None:
        """Set callback function to be called when new data arrives."""
        self.data_callback = callback

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client receives a CONNACK response from the server."""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            # Subscribe to all weather station topics
            client.subscribe("backacres/house/weatherstation/#")
            self.logger.info("Subscribed to weather station topics")
        else:
            self.logger.error(f"Failed to connect to MQTT broker, return code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the server."""
        if rc != 0:
            self.logger.warning("Unexpected disconnection from MQTT broker")
        else:
            self.logger.info("Disconnected from MQTT broker")

    def _on_message(self, client, userdata, msg):
        """Callback for when a PUBLISH message is received from the server."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')

            # Parse JSON data
            data = json.loads(payload)

            self.logger.info(f"Received data from {topic}: {data}")

            # Store data in database based on topic
            if "weathermeters" in topic:
                self.database.insert_weather_data(data)
                self.logger.info("Stored weather data in database")
            elif "magneticfluxsensor" in topic:
                self.database.insert_magnetic_flux_data(data)
                self.logger.info("Stored magnetic flux data in database")

            # Call data callback if set (for real-time GUI updates)
            if self.data_callback:
                self.data_callback(topic, data)

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from {msg.topic}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message from {msg.topic}: {e}")

    def start(self) -> None:
        """Start the MQTT subscriber."""
        try:
            self.logger.info(f"Connecting to MQTT broker at {self.host}:{self.port}")
            self.client.connect(self.host, self.port, 60)
            self.running = True

            # Start the network loop in a separate thread
            self.client.loop_start()

        except Exception as e:
            self.logger.error(f"Failed to start MQTT subscriber: {e}")
            raise

    def stop(self) -> None:
        """Stop the MQTT subscriber."""
        self.logger.info("Stopping MQTT subscriber")
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()

    def is_connected(self) -> bool:
        """Check if the MQTT client is connected."""
        return self.client.is_connected()


def main():
    """Main function for testing the MQTT subscriber."""
    subscriber = WeatherMQTTSubscriber()

    try:
        subscriber.start()

        # Keep the subscriber running
        import time
        while True:
            time.sleep(1)
            if not subscriber.is_connected():
                print("Disconnected from MQTT broker, attempting to reconnect...")
                subscriber.start()

    except KeyboardInterrupt:
        print("\nShutting down MQTT subscriber...")
        subscriber.stop()


if __name__ == "__main__":
    main()