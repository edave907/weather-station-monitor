#!/usr/bin/env python3
"""
USGS Magnetic Data Importer for Weather Station Database

This utility fetches magnetic field data from USGS geomagnetic observatories
and imports it into the weather station database for comparison with local
HMC5883L sensor measurements.

Features:
- Fetches data from any USGS observatory
- Converts USGS nanotesla data to format compatible with 3D plotter
- Creates separate table for USGS reference data
- Time range selection with automatic chunking for large datasets
- Unit conversion between nT (USGS) and Tesla (NIST SP 330)
- Observatory location metadata storage

Usage:
    python usgs_magnetic_importer.py --observatory BOU --hours 24
    python usgs_magnetic_importer.py --observatory FRD --start "2025-10-01" --end "2025-10-05"
    python usgs_magnetic_importer.py --list-observatories

Observatories:
    BOU - Boulder, Colorado (recommended for western US)
    FRD - Fredericksburg, Virginia (recommended for eastern US)
    TUC - Tucson, Arizona
    HON - Honolulu, Hawaii
    SJG - San Juan, Puerto Rico

Data Format:
    USGS data is stored in 'usgs_magnetic_data' table with same X,Y,Z structure
    as local 'magnetic_flux_data' table, enabling direct comparison in 3D plotter.
"""

import argparse
import requests
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time

class USGSMagneticImporter:
    """Imports USGS magnetic observatory data into weather station database."""

    # Observatory codes and locations
    OBSERVATORIES = {
        'CMO': {'name': 'College', 'state': 'Alaska', 'country': 'USA'},
        'BOU': {'name': 'Boulder', 'state': 'Colorado', 'country': 'USA'},
        'BRW': {'name': 'Barrow', 'state': 'Alaska', 'country': 'USA'},
        'BSL': {'name': 'Stennis', 'state': 'Mississippi', 'country': 'USA'},
        'DED': {'name': 'Deadhorse', 'state': 'Alaska', 'country': 'USA'},
        'FRD': {'name': 'Fredericksburg', 'state': 'Virginia', 'country': 'USA'},
        'FRN': {'name': 'Fresno', 'state': 'California', 'country': 'USA'},
        'GUA': {'name': 'Guam', 'state': 'Guam', 'country': 'USA'},
        'HON': {'name': 'Honolulu', 'state': 'Hawaii', 'country': 'USA'},
        'NEW': {'name': 'Newport', 'state': 'Washington', 'country': 'USA'},
        'SHU': {'name': 'Shumagin', 'state': 'Alaska', 'country': 'USA'},
        'SIT': {'name': 'Sitka', 'state': 'Alaska', 'country': 'USA'},
        'SJG': {'name': 'San Juan', 'state': 'Puerto Rico', 'country': 'USA'},
        'TUC': {'name': 'Tucson', 'state': 'Arizona', 'country': 'USA'}
    }

    def __init__(self, db_path: str = "weather_data.db"):
        self.db_path = db_path
        self.base_url = "https://geomag.usgs.gov/ws/data/"
        self.init_database()

    def init_database(self) -> None:
        """Initialize USGS magnetic data table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create USGS magnetic data table (same structure as local data for compatibility)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usgs_magnetic_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observatory_code TEXT NOT NULL,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    z REAL NOT NULL,
                    f REAL,
                    data_timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_type TEXT DEFAULT 'variation',
                    UNIQUE(observatory_code, data_timestamp) ON CONFLICT REPLACE
                )
            """)

            # Create observatory metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usgs_observatories (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    state TEXT,
                    country TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usgs_timestamp ON usgs_magnetic_data(data_timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usgs_observatory ON usgs_magnetic_data(observatory_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usgs_created ON usgs_magnetic_data(created_at)")

            conn.commit()

    def store_observatory_metadata(self, observatory_code: str) -> None:
        """Store observatory metadata in database."""
        if observatory_code not in self.OBSERVATORIES:
            return

        obs_info = self.OBSERVATORIES[observatory_code]
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO usgs_observatories (code, name, state, country)
                VALUES (?, ?, ?, ?)
            """, (observatory_code, obs_info['name'], obs_info['state'], obs_info['country']))
            conn.commit()

    def fetch_usgs_data(self, observatory_code: str, start_time: datetime,
                       end_time: datetime, sampling_period: int = 60) -> Optional[Dict]:
        """Fetch magnetic data from USGS API."""
        params = {
            'id': observatory_code,
            'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'format': 'json',
            'elements': 'X,Y,Z,F',
            'sampling_period': sampling_period,
            'type': 'variation'  # Real-time variation data
        }

        print(f"Fetching data from {observatory_code} ({start_time} to {end_time})...")

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            if 'times' not in data or 'values' not in data:
                print(f"Warning: No data returned for {observatory_code}")
                return None

            print(f"Retrieved {len(data['times'])} data points from {observatory_code}")
            return data

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from USGS API: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return None

    def convert_usgs_to_tesla(self, nanoTesla_value: float) -> float:
        """Convert USGS nanotesla values to Tesla (NIST SP 330 units)."""
        # 1 nT = 1e-9 T
        return nanoTesla_value * 1e-9

    def process_and_store_data(self, observatory_code: str, usgs_data: Dict) -> int:
        """Process USGS data and store in database with Tesla units."""
        if not usgs_data or 'times' not in usgs_data or 'values' not in usgs_data:
            return 0

        times = usgs_data['times']
        values = usgs_data['values']

        print(f"Processing USGS data structure:")
        print(f"  Times: {len(times)} entries")
        print(f"  Values: {len(values)} component series")

        # USGS API returns data with each component as a separate series
        # Extract individual component data
        component_data = {}
        for series in values:
            if isinstance(series, dict) and 'id' in series and 'values' in series:
                component_id = series['id']
                component_values = series['values']
                component_data[component_id] = component_values
                print(f"  Found component {component_id}: {len(component_values)} values")

        # Ensure we have all required components
        if 'X' not in component_data or 'Y' not in component_data or 'Z' not in component_data:
            print("Error: Missing required X, Y, or Z components")
            return 0

        # Get the minimum length to avoid index errors
        min_length = min(len(times), len(component_data['X']), len(component_data['Y']), len(component_data['Z']))

        stored_count = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for i in range(min_length):
                # Parse timestamp
                try:
                    timestamp_str = times[i]
                    if timestamp_str.endswith('Z'):
                        data_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        data_timestamp = datetime.fromisoformat(timestamp_str)
                except (ValueError, IndexError) as e:
                    print(f"Error parsing timestamp {i}: {e}")
                    continue

                # Extract component values (already in nanotesla)
                try:
                    x_nt = component_data['X'][i] if component_data['X'][i] is not None else 0
                    y_nt = component_data['Y'][i] if component_data['Y'][i] is not None else 0
                    z_nt = component_data['Z'][i] if component_data['Z'][i] is not None else 0
                    f_nt = component_data.get('F', [None] * len(times))[i] if 'F' in component_data else None
                except (IndexError, TypeError):
                    continue

                # Convert nanotesla to Tesla for NIST SP 330 compliance
                x_tesla = self.convert_usgs_to_tesla(x_nt)
                y_tesla = self.convert_usgs_to_tesla(y_nt)
                z_tesla = self.convert_usgs_to_tesla(z_nt)
                f_tesla = self.convert_usgs_to_tesla(f_nt) if f_nt is not None else None

                # Store in database
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO usgs_magnetic_data
                        (observatory_code, x, y, z, f, data_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (observatory_code, x_tesla, y_tesla, z_tesla, f_tesla, data_timestamp))
                    stored_count += 1
                except sqlite3.Error as e:
                    print(f"Database error: {e}")
                    continue

            conn.commit()

        print(f"Successfully stored {stored_count} records")
        return stored_count

    def import_data_range(self, observatory_code: str, start_time: datetime,
                         end_time: datetime, chunk_hours: int = 24) -> int:
        """Import data for a time range, chunking large requests."""
        observatory_code = observatory_code.upper()

        if observatory_code not in self.OBSERVATORIES:
            print(f"Error: Observatory '{observatory_code}' not found.")
            print("Available observatories:", ', '.join(self.OBSERVATORIES.keys()))
            return 0

        # Store observatory metadata
        self.store_observatory_metadata(observatory_code)

        total_stored = 0
        current_start = start_time

        while current_start < end_time:
            chunk_end = min(current_start + timedelta(hours=chunk_hours), end_time)

            # Fetch data chunk
            data = self.fetch_usgs_data(observatory_code, current_start, chunk_end)

            if data:
                stored = self.process_and_store_data(observatory_code, data)
                total_stored += stored
                print(f"Stored {stored} records for {current_start.date()}")

            current_start = chunk_end

            # Rate limiting - be respectful to USGS servers
            time.sleep(0.5)

        return total_stored

    def list_observatories(self) -> None:
        """List available USGS observatories."""
        print("Available USGS Geomagnetic Observatories:")
        print("=" * 50)
        for code, info in self.OBSERVATORIES.items():
            print(f"{code} - {info['name']}, {info['state']}, {info['country']}")

    def get_data_summary(self, observatory_code: str = None) -> None:
        """Display summary of imported USGS data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if observatory_code:
                cursor.execute("""
                    SELECT COUNT(*), MIN(data_timestamp), MAX(data_timestamp)
                    FROM usgs_magnetic_data
                    WHERE observatory_code = ?
                """, (observatory_code.upper(),))
            else:
                cursor.execute("""
                    SELECT observatory_code, COUNT(*), MIN(data_timestamp), MAX(data_timestamp)
                    FROM usgs_magnetic_data
                    GROUP BY observatory_code
                    ORDER BY observatory_code
                """)

            results = cursor.fetchall()

            if not results:
                print("No USGS magnetic data found in database.")
                return

            print("USGS Magnetic Data Summary:")
            print("=" * 60)

            if observatory_code:
                count, min_time, max_time = results[0]
                print(f"Observatory: {observatory_code.upper()}")
                print(f"Records: {count:,}")
                print(f"Time range: {min_time} to {max_time}")
            else:
                for row in results:
                    obs_code, count, min_time, max_time = row
                    obs_info = self.OBSERVATORIES.get(obs_code, {})
                    location = f"{obs_info.get('name', 'Unknown')}, {obs_info.get('state', 'Unknown')}"
                    print(f"{obs_code} ({location}): {count:,} records ({min_time} to {max_time})")

def main():
    parser = argparse.ArgumentParser(description='Import USGS magnetic observatory data')
    parser.add_argument('--observatory', '-o', help='Observatory code (e.g., BOU, FRD, TUC)')
    parser.add_argument('--start', help='Start time (YYYY-MM-DD or "YYYY-MM-DD HH:MM")')
    parser.add_argument('--end', help='End time (YYYY-MM-DD or "YYYY-MM-DD HH:MM")')
    parser.add_argument('--hours', type=int, help='Hours of recent data to import')
    parser.add_argument('--days', type=int, help='Days of recent data to import')
    parser.add_argument('--db', default='weather_data.db', help='Database path')
    parser.add_argument('--list-observatories', action='store_true', help='List available observatories')
    parser.add_argument('--summary', action='store_true', help='Show data summary')
    parser.add_argument('--chunk-hours', type=int, default=24, help='Hours per API request chunk')

    args = parser.parse_args()

    importer = USGSMagneticImporter(args.db)

    if args.list_observatories:
        importer.list_observatories()
        return

    if args.summary:
        importer.get_data_summary(args.observatory)
        return

    if not args.observatory:
        print("Error: Observatory code required. Use --list-observatories to see options.")
        return

    # Calculate time range
    end_time = datetime.now()

    if args.hours:
        start_time = end_time - timedelta(hours=args.hours)
    elif args.days:
        start_time = end_time - timedelta(days=args.days)
    elif args.start and args.end:
        try:
            start_time = datetime.fromisoformat(args.start)
            end_time = datetime.fromisoformat(args.end)
        except ValueError as e:
            print(f"Error parsing dates: {e}")
            print("Use format: YYYY-MM-DD or 'YYYY-MM-DD HH:MM'")
            return
    else:
        # Default to last 24 hours
        start_time = end_time - timedelta(hours=24)
        print("No time range specified, using last 24 hours")

    print(f"Importing data from {args.observatory} for {start_time} to {end_time}")

    # Import data
    total_imported = importer.import_data_range(
        args.observatory, start_time, end_time, args.chunk_hours
    )

    print(f"\nImport complete: {total_imported:,} records imported from {args.observatory}")

    # Show summary
    importer.get_data_summary(args.observatory)

if __name__ == "__main__":
    main()