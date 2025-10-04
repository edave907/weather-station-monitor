"""
Database interface for weather station data storage and retrieval.
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class WeatherDatabase:
    """Handles weather station data storage and retrieval."""

    def __init__(self, db_path: str = "weather_data.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self) -> None:
        """Initialize database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Weather data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS weather_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    sample_interval INTEGER,
                    temperature REAL,
                    humidity REAL,
                    pressure REAL,
                    irradiance REAL,
                    wind_direction INTEGER,
                    rain_gauge_count INTEGER,
                    anemometer_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Magnetic flux sensor data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS magnetic_flux_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    z REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_timestamp ON weather_data(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_created ON weather_data(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flux_created ON magnetic_flux_data(created_at)")

            conn.commit()

    def insert_weather_data(self, data: Dict) -> None:
        """Insert weather data into the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO weather_data
                (timestamp, sample_interval, temperature, humidity, pressure,
                 irradiance, wind_direction, rain_gauge_count, anemometer_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('utc'),
                data.get('sampleinterval'),
                data.get('temperature'),
                data.get('humidity'),
                data.get('pressure'),
                data.get('irradiance'),
                data.get('winddirectionsensor'),
                data.get('raingaugecount'),
                data.get('anemometercount')
            ))
            conn.commit()

    def insert_magnetic_flux_data(self, data: Dict) -> None:
        """Insert magnetic flux data into the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO magnetic_flux_data (x, y, z)
                VALUES (?, ?, ?)
            """, (data.get('x'), data.get('y'), data.get('z')))
            conn.commit()

    def get_latest_weather_data(self, limit: int = 100) -> List[Tuple]:
        """Get the latest weather data entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, temperature, humidity, pressure, irradiance,
                       wind_direction, rain_gauge_count, anemometer_count, created_at
                FROM weather_data
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()

    def get_weather_data_range(self, start_time: datetime, end_time: datetime) -> List[Tuple]:
        """Get weather data within a specific time range."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, temperature, humidity, pressure, irradiance,
                       wind_direction, rain_gauge_count, anemometer_count, created_at
                FROM weather_data
                WHERE created_at BETWEEN ? AND ?
                ORDER BY created_at ASC
            """, (start_time, end_time))
            return cursor.fetchall()

    def get_latest_magnetic_flux_data(self, limit: int = 100) -> List[Tuple]:
        """Get the latest magnetic flux data entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT x, y, z, created_at
                FROM magnetic_flux_data
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()

    def get_magnetic_flux_data_range(self, start_time: datetime, end_time: datetime) -> List[Tuple]:
        """Get magnetic flux data within a specific time range."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT x, y, z, created_at
                FROM magnetic_flux_data
                WHERE created_at BETWEEN ? AND ?
                ORDER BY created_at ASC
            """, (start_time, end_time))
            return cursor.fetchall()

    def get_current_weather_summary(self) -> Optional[Dict]:
        """Get the most recent weather reading as a summary."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT temperature, humidity, pressure, irradiance,
                       wind_direction, rain_gauge_count, anemometer_count, created_at
                FROM weather_data
                ORDER BY created_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return {
                    'temperature': row[0],
                    'humidity': row[1],
                    'pressure': row[2],
                    'irradiance': row[3],
                    'wind_direction': row[4],
                    'rain_gauge_count': row[5],
                    'anemometer_count': row[6],
                    'last_updated': row[7]
                }
            return None