#!/usr/bin/env python3
"""
Test script to verify weather station components work correctly.
"""

import json
import time
import threading
from database import WeatherDatabase
from mqtt_subscriber import WeatherMQTTSubscriber


def test_database():
    """Test database functionality."""
    print("Testing database...")

    # Create test database
    db = WeatherDatabase("test_weather.db")

    # Test weather data insertion
    test_weather_data = {
        'utc': int(time.time()),
        'sampleinterval': 5000,
        'temperature': 22.5,
        'humidity': 65.2,
        'pressure': 1013.25,
        'irradiance': 0.85,
        'winddirectionsensor': 180,
        'raingaugecount': 42,
        'anemometercount': 1000
    }

    db.insert_weather_data(test_weather_data)
    print("✓ Weather data inserted")

    # Test magnetic flux data insertion
    test_flux_data = {
        'x': 100.5,
        'y': -50.2,
        'z': -25.8
    }

    db.insert_magnetic_flux_data(test_flux_data)
    print("✓ Magnetic flux data inserted")

    # Test data retrieval
    weather_data = db.get_latest_weather_data(1)
    if weather_data:
        print(f"✓ Retrieved weather data: {weather_data[0]}")
    else:
        print("✗ No weather data retrieved")

    flux_data = db.get_latest_magnetic_flux_data(1)
    if flux_data:
        print(f"✓ Retrieved flux data: {flux_data[0]}")
    else:
        print("✗ No flux data retrieved")

    # Test summary
    summary = db.get_current_weather_summary()
    if summary:
        print(f"✓ Weather summary: Temperature={summary['temperature']}°C, Humidity={summary['humidity']}%")
    else:
        print("✗ No weather summary available")

    print("Database test completed.\n")


def test_mqtt_subscriber():
    """Test MQTT subscriber (requires MQTT broker)."""
    print("Testing MQTT subscriber...")

    received_data = []

    def data_callback(topic, data):
        received_data.append((topic, data))
        print(f"✓ Received data from {topic}: {data}")

    subscriber = WeatherMQTTSubscriber(db_path="test_weather.db")
    subscriber.set_data_callback(data_callback)

    try:
        subscriber.start()
        print("✓ MQTT subscriber started")

        # Wait for connection
        time.sleep(2)

        if subscriber.is_connected():
            print("✓ Connected to MQTT broker")
        else:
            print("✗ Failed to connect to MQTT broker")
            print("  Make sure mosquitto broker is running: sudo systemctl start mosquitto")

        # Wait for some data (or timeout)
        print("Waiting for data (10 seconds)...")
        time.sleep(10)

        subscriber.stop()
        print("✓ MQTT subscriber stopped")

        if received_data:
            print(f"✓ Received {len(received_data)} messages")
        else:
            print("! No data received (this is normal if no MQTT data is being published)")

    except Exception as e:
        print(f"✗ MQTT test failed: {e}")

    print("MQTT subscriber test completed.\n")


def simulate_mqtt_data():
    """Simulate MQTT data for testing."""
    print("Simulating MQTT data...")

    db = WeatherDatabase("test_weather.db")

    # Simulate weather data
    for i in range(5):
        test_data = {
            'utc': int(time.time()) + i,
            'sampleinterval': 5000,
            'temperature': 20.0 + i * 0.5,
            'humidity': 60.0 + i,
            'pressure': 1013.0 + i * 0.1,
            'irradiance': 0.8 + i * 0.01,
            'winddirectionsensor': 180 + i * 10,
            'raingaugecount': 40 + i,
            'anemometercount': 1000 + i * 10
        }

        db.insert_weather_data(test_data)
        print(f"✓ Inserted simulated weather data #{i + 1}")

        # Simulate magnetic flux data
        flux_data = {
            'x': 100.0 + i,
            'y': -50.0 - i,
            'z': -25.0 + i * 0.5
        }

        db.insert_magnetic_flux_data(flux_data)
        print(f"✓ Inserted simulated flux data #{i + 1}")

        time.sleep(0.1)

    print("Data simulation completed.\n")


def main():
    """Run all tests."""
    print("Weather Station Component Tests")
    print("===============================\n")

    # Test database
    test_database()

    # Simulate some data
    simulate_mqtt_data()

    # Test MQTT subscriber
    test_mqtt_subscriber()

    print("All tests completed!")
    print("\nTo run the main application:")
    print("  python main.py              # GTK GUI mode")
    print("  python main.py --console    # Console mode")
    print("\nTo clean up test database:")
    print("  rm test_weather.db")


if __name__ == "__main__":
    main()