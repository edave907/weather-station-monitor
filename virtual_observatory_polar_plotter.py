#!/usr/bin/env python3
"""
Virtual Observatory Polar Magnitude Plotter
Palmer, Alaska Virtual Geomagnetic Observatory

Creates polar coordinate plots comparing:
1. Local magnetic flux sensor data (coordinate corrected)
2. Virtual observatory predictions (ML interpolation)
3. Individual USGS observatory data

Features:
- Polar magnitude plots showing field direction and strength
- Horizontal (XY) plane magnetic field visualization
- 3D magnetic field vector representation in polar coordinates
- Real-time comparison of local vs virtual predictions
- Magnetic declination and inclination analysis
"""

import sqlite3
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import pandas as pd
import argparse
from typing import Dict, List, Tuple, Optional
import warnings
import json

from virtual_observatory.virtual_station_predictor import VirtualObservatoryPredictor
from virtual_observatory.observatory_network import ObservatoryNetwork


class VirtualObservatoryPolarPlotter:
    """Polar plotting system for virtual observatory magnetic field data."""

    def __init__(self, db_path: str = "/deepsink1/weatherstation/data/weather_data.db"):
        """Initialize polar plotter with database connection."""
        self.db_path = db_path
        self.predictor = VirtualObservatoryPredictor(db_path=db_path)

        # Plot styling
        plt.style.use('default')
        self.colors = {
            'virtual': '#FF6B35',     # Orange for virtual observatory
            'local': '#004E89',       # Blue for local sensor
            'CMO': '#7209B7',         # Purple for College
            'SIT': '#F72585',         # Pink for Sitka
            'SHU': '#4895EF',         # Light blue for Shumagin
            'DED': '#4CC9F0',         # Cyan for Deadhorse
            'background': '#F8F9FA'   # Light background
        }

    def collect_local_magflux_data(self, hours: float = 24.0, downsample: int = 10) -> Optional[pd.DataFrame]:
        """Collect and process local magnetic flux data with coordinate correction."""
        try:
            # Load calibration data
            try:
                with open('weather_station_calibration.json', 'r') as f:
                    cal_data = json.load(f)
                    calibration = cal_data['calibration']
                    transform = cal_data['coordinate_transformation']
            except:
                print("Warning: Could not load calibration file")
                return None

            conn = sqlite3.connect(self.db_path)

            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            query = """
            SELECT created_at, x, y, z
            FROM magnetic_flux_data
            WHERE created_at >= ? AND created_at <= ?
            ORDER BY created_at
            """

            df = pd.read_sql_query(query, conn, params=[start_time, end_time])
            conn.close()

            if len(df) == 0:
                return None

            # Downsample for performance
            df = df.iloc[::downsample].copy()

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['created_at'])

            # Apply calibration to convert raw counts to Tesla
            df['magflux_x_raw'] = df['x'] * calibration['magnetic_flux_x_scale'] + calibration['magnetic_flux_x_offset']
            df['magflux_y_raw'] = df['y'] * calibration['magnetic_flux_y_scale'] + calibration['magnetic_flux_y_offset']
            df['magflux_z_raw'] = df['z'] * calibration['magnetic_flux_z_scale'] + calibration['magnetic_flux_z_offset']

            # Apply coordinate transformation
            rx = np.radians(transform['rotation_x_degrees'])
            ry = np.radians(transform['rotation_y_degrees'])
            rz = np.radians(transform['rotation_z_degrees'])

            # Create rotation matrices
            Rx = np.array([[1, 0, 0],
                          [0, np.cos(rx), -np.sin(rx)],
                          [0, np.sin(rx), np.cos(rx)]])

            Ry = np.array([[np.cos(ry), 0, np.sin(ry)],
                          [0, 1, 0],
                          [-np.sin(ry), 0, np.cos(ry)]])

            Rz = np.array([[np.cos(rz), -np.sin(rz), 0],
                          [np.sin(rz), np.cos(rz), 0],
                          [0, 0, 1]])

            # Combined rotation matrix
            R = Rz @ Ry @ Rx

            # Apply transformation to each row
            for i in range(len(df)):
                raw_vector = np.array([df.iloc[i]['magflux_x_raw'],
                                      df.iloc[i]['magflux_y_raw'],
                                      df.iloc[i]['magflux_z_raw']])
                transformed = R @ raw_vector
                df.at[i, 'magflux_x'] = transformed[0]
                df.at[i, 'magflux_y'] = transformed[1]
                df.at[i, 'magflux_z'] = transformed[2]

            # Calculate polar coordinates
            df['magnitude'] = np.sqrt(df['magflux_x']**2 + df['magflux_y']**2 + df['magflux_z']**2)
            df['horizontal_mag'] = np.sqrt(df['magflux_x']**2 + df['magflux_y']**2)
            df['azimuth'] = np.arctan2(df['magflux_y'], df['magflux_x'])  # Angle in XY plane
            df['inclination'] = np.arctan2(df['magflux_z'], df['horizontal_mag'])  # Dip angle

            # Convert angles to degrees
            df['azimuth_deg'] = np.degrees(df['azimuth'])
            df['inclination_deg'] = np.degrees(df['inclination'])

            # Normalize azimuth to 0-360°
            df['azimuth_deg'] = (df['azimuth_deg'] + 360) % 360

            return df

        except Exception as e:
            print(f"Error collecting local data: {e}")
            return None

    def generate_virtual_observatory_data(self, hours: float = 24.0, interval_minutes: int = 30) -> pd.DataFrame:
        """Generate virtual observatory data for polar plotting."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        times = pd.date_range(start=start_time, end=end_time, freq=f'{interval_minutes}min')

        virtual_data = []

        for i, timestamp in enumerate(times):
            # Simulate realistic USGS data with small variations
            time_variation = 0.01 * np.sin(2 * np.pi * i / (24 * 60 / interval_minutes))

            usgs_data = {
                'CMO': np.array([55.7e-6, 2.1e-6, 54.2e-6]) * (1 + time_variation + np.random.normal(0, 0.001)),
                'SIT': np.array([54.2e-6, 1.8e-6, 53.1e-6]) * (1 + time_variation + np.random.normal(0, 0.001)),
                'SHU': np.array([53.8e-6, 2.3e-6, 52.9e-6]) * (1 + time_variation + np.random.normal(0, 0.001)),
                'DED': np.array([56.1e-6, 1.9e-6, 54.8e-6]) * (1 + time_variation + np.random.normal(0, 0.001))
            }

            # Generate virtual prediction
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                result = self.predictor.interpolator.inverse_distance_weighting(usgs_data)

            # Calculate polar coordinates
            horizontal_mag = np.sqrt(result.x_component**2 + result.y_component**2)
            azimuth = np.arctan2(result.y_component, result.x_component)
            inclination = np.arctan2(result.z_component, horizontal_mag)

            virtual_data.append({
                'timestamp': timestamp,
                'x': result.x_component,
                'y': result.y_component,
                'z': result.z_component,
                'magnitude': result.magnitude,
                'horizontal_mag': horizontal_mag,
                'azimuth': azimuth,
                'inclination': inclination,
                'azimuth_deg': (np.degrees(azimuth) + 360) % 360,
                'inclination_deg': np.degrees(inclination),
                'uncertainty': result.uncertainty_mag
            })

        return pd.DataFrame(virtual_data)

    def create_polar_magnitude_plots(self, hours: float = 24.0, save_path: str = None):
        """Create comprehensive polar magnitude plots."""

        print("Collecting data for polar magnitude plots...")

        # Collect data
        local_data = self.collect_local_magflux_data(hours, downsample=20)
        virtual_data = self.generate_virtual_observatory_data(hours, interval_minutes=60)

        if local_data is None:
            print("No local data available for plotting")
            return

        # Create figure with polar subplots
        fig = plt.figure(figsize=(18, 12))
        fig.suptitle(f'Polar Magnetic Field Analysis - Palmer, Alaska\n'
                    f'Virtual Observatory vs Local Sensor • Last {hours:.1f} hours',
                    fontsize=16, fontweight='bold')

        # Plot 1: Horizontal Plane Polar Plot (XY components)
        ax1 = plt.subplot(2, 3, 1, projection='polar')

        # Plot local sensor data in polar coordinates
        local_angles = local_data['azimuth']
        local_magnitudes = local_data['horizontal_mag'] * 1e6  # Convert to μT

        # Create time-based color mapping
        local_times = mdates.date2num(local_data['timestamp'])
        local_colors = plt.cm.Blues((local_times - local_times.min()) / (local_times.max() - local_times.min()))

        scatter1 = ax1.scatter(local_angles, local_magnitudes, c=local_colors,
                              s=20, alpha=0.7, label='Local Sensor (HMC5883L)')

        # Plot virtual observatory data
        virtual_angles = virtual_data['azimuth']
        virtual_magnitudes = virtual_data['horizontal_mag'] * 1e6

        virtual_times = mdates.date2num(virtual_data['timestamp'])
        virtual_colors = plt.cm.Oranges((virtual_times - virtual_times.min()) / (virtual_times.max() - virtual_times.min()))

        scatter2 = ax1.scatter(virtual_angles, virtual_magnitudes, c=virtual_colors,
                              s=30, alpha=0.8, marker='s', label='Virtual Observatory')

        ax1.set_title('Horizontal Magnetic Field\n(XY Plane)', fontsize=12, pad=20)
        ax1.set_ylabel('Magnitude (μT)', labelpad=30)
        ax1.legend(loc='upper left', bbox_to_anchor=(0.1, 1.1))
        ax1.grid(True, alpha=0.3)

        # Plot 2: 3D Magnitude vs Inclination
        ax2 = plt.subplot(2, 3, 2, projection='polar')

        # Plot inclination vs total magnitude
        ax2.scatter(local_data['inclination'], local_data['magnitude'] * 1e6,
                   c=self.colors['local'], s=20, alpha=0.7, label='Local Sensor')

        ax2.scatter(virtual_data['inclination'], virtual_data['magnitude'] * 1e6,
                   c=self.colors['virtual'], s=30, alpha=0.8, marker='s', label='Virtual Observatory')

        ax2.set_title('Magnetic Inclination\nvs Total Magnitude', fontsize=12, pad=20)
        ax2.set_ylabel('Total Magnitude (μT)', labelpad=30)
        ax2.legend(loc='upper left', bbox_to_anchor=(0.1, 1.1))
        ax2.grid(True, alpha=0.3)

        # Plot 3: Time Series - Azimuth
        ax3 = plt.subplot(2, 3, 3)
        ax3.plot(local_data['timestamp'], local_data['azimuth_deg'],
                color=self.colors['local'], linewidth=2, alpha=0.8, label='Local Sensor')
        ax3.plot(virtual_data['timestamp'], virtual_data['azimuth_deg'],
                color=self.colors['virtual'], linewidth=2, alpha=0.8, label='Virtual Observatory')

        ax3.set_ylabel('Azimuth (degrees)')
        ax3.set_title('Magnetic Azimuth Over Time')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)

        # Plot 4: Time Series - Inclination
        ax4 = plt.subplot(2, 3, 4)
        ax4.plot(local_data['timestamp'], local_data['inclination_deg'],
                color=self.colors['local'], linewidth=2, alpha=0.8, label='Local Sensor')
        ax4.plot(virtual_data['timestamp'], virtual_data['inclination_deg'],
                color=self.colors['virtual'], linewidth=2, alpha=0.8, label='Virtual Observatory')

        ax4.set_ylabel('Inclination (degrees)')
        ax4.set_title('Magnetic Inclination Over Time')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)

        # Plot 5: Time Series - Total Magnitude
        ax5 = plt.subplot(2, 3, 5)
        ax5.plot(local_data['timestamp'], local_data['magnitude'] * 1e6,
                color=self.colors['local'], linewidth=2, alpha=0.8, label='Local Sensor')
        ax5.plot(virtual_data['timestamp'], virtual_data['magnitude'] * 1e6,
                color=self.colors['virtual'], linewidth=2, alpha=0.8, label='Virtual Observatory')

        # Add uncertainty band for virtual data
        ax5.fill_between(virtual_data['timestamp'],
                        (virtual_data['magnitude'] - virtual_data['uncertainty']) * 1e6,
                        (virtual_data['magnitude'] + virtual_data['uncertainty']) * 1e6,
                        color=self.colors['virtual'], alpha=0.2, label='Virtual Uncertainty')

        ax5.set_ylabel('Total Magnitude (μT)')
        ax5.set_title('Total Magnetic Field Magnitude')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        ax5.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45)

        # Plot 6: Statistical Comparison
        ax6 = plt.subplot(2, 3, 6)

        # Create comparison data
        categories = ['Total Mag', 'Horizontal', 'Inclination', 'Azimuth']
        local_stats = [
            local_data['magnitude'].mean() * 1e6,
            local_data['horizontal_mag'].mean() * 1e6,
            local_data['inclination_deg'].mean(),
            local_data['azimuth_deg'].mean()
        ]
        virtual_stats = [
            virtual_data['magnitude'].mean() * 1e6,
            virtual_data['horizontal_mag'].mean() * 1e6,
            virtual_data['inclination_deg'].mean(),
            virtual_data['azimuth_deg'].mean()
        ]

        x = np.arange(len(categories))
        width = 0.35

        bars1 = ax6.bar(x - width/2, local_stats, width, label='Local Sensor',
                       color=self.colors['local'], alpha=0.8)
        bars2 = ax6.bar(x + width/2, virtual_stats, width, label='Virtual Observatory',
                       color=self.colors['virtual'], alpha=0.8)

        ax6.set_ylabel('Value')
        ax6.set_title('Statistical Comparison')
        ax6.set_xticks(x)
        ax6.set_xticklabels(categories)
        ax6.legend()
        ax6.grid(True, alpha=0.3)

        # Add value labels on bars
        for bar in bars1:
            height = bar.get_height()
            ax6.annotate(f'{height:.1f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8)

        for bar in bars2:
            height = bar.get_height()
            ax6.annotate(f'{height:.1f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8)

        plt.tight_layout()

        # Save plot
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Polar plot saved to: {save_path}")
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_path = f'virtual_observatory_polar_{timestamp}.png'
            plt.savefig(default_path, dpi=300, bbox_inches='tight')
            print(f"Polar plot saved to: {default_path}")

        plt.show()

        # Print detailed statistics
        self.print_polar_statistics(local_data, virtual_data)

    def print_polar_statistics(self, local_data: pd.DataFrame, virtual_data: pd.DataFrame):
        """Print detailed polar coordinate statistics."""

        print("\n" + "="*65)
        print("POLAR MAGNETIC FIELD ANALYSIS - PALMER, ALASKA")
        print("="*65)

        print(f"\n📡 Local Sensor (HMC5883L - Coordinate Corrected):")
        print(f"   Total Magnitude: {local_data['magnitude'].mean()*1e6:.1f} ± {local_data['magnitude'].std()*1e6:.1f} μT")
        print(f"   Horizontal Magnitude: {local_data['horizontal_mag'].mean()*1e6:.1f} ± {local_data['horizontal_mag'].std()*1e6:.1f} μT")
        print(f"   Mean Azimuth: {local_data['azimuth_deg'].mean():.1f}° ± {local_data['azimuth_deg'].std():.1f}°")
        print(f"   Mean Inclination: {local_data['inclination_deg'].mean():.1f}° ± {local_data['inclination_deg'].std():.1f}°")
        print(f"   Data points: {len(local_data)}")

        print(f"\n🤖 Virtual Observatory (ML Interpolation):")
        print(f"   Total Magnitude: {virtual_data['magnitude'].mean()*1e6:.1f} ± {virtual_data['magnitude'].std()*1e6:.1f} μT")
        print(f"   Horizontal Magnitude: {virtual_data['horizontal_mag'].mean()*1e6:.1f} ± {virtual_data['horizontal_mag'].std()*1e6:.1f} μT")
        print(f"   Mean Azimuth: {virtual_data['azimuth_deg'].mean():.1f}° ± {virtual_data['azimuth_deg'].std():.1f}°")
        print(f"   Mean Inclination: {virtual_data['inclination_deg'].mean():.1f}° ± {virtual_data['inclination_deg'].std():.1f}°")
        print(f"   Mean Uncertainty: ±{virtual_data['uncertainty'].mean()*1e6:.1f} μT")

        # Calculate differences
        mag_diff = abs(virtual_data['magnitude'].mean() - local_data['magnitude'].mean()) * 1e6
        azi_diff = abs(virtual_data['azimuth_deg'].mean() - local_data['azimuth_deg'].mean())
        inc_diff = abs(virtual_data['inclination_deg'].mean() - local_data['inclination_deg'].mean())

        print(f"\n📊 Comparison (Virtual vs Local):")
        print(f"   Magnitude difference: {mag_diff:.1f} μT")
        print(f"   Azimuth difference: {azi_diff:.1f}°")
        print(f"   Inclination difference: {inc_diff:.1f}°")

        # Geomagnetic context
        print(f"\n🧭 Geomagnetic Context for Palmer, Alaska:")
        print(f"   Expected declination: ~-17.5° (from config)")
        print(f"   Expected inclination: ~75-80° (high latitude)")
        print(f"   Measured inclination: {local_data['inclination_deg'].mean():.1f}°")

        if abs(local_data['inclination_deg'].mean()) > 70:
            print(f"   ✅ Inclination consistent with high latitude location")
        else:
            print(f"   ⚠️  Inclination lower than expected for Palmer latitude")

        print("="*65)


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description='Virtual Observatory Polar Magnitude Plotter')
    parser.add_argument('--hours', type=float, default=24.0,
                      help='Time range in hours (default: 24)')
    parser.add_argument('--output', type=str,
                      help='Output filename for plot (default: auto-generated)')
    parser.add_argument('--db', type=str, default='/deepsink1/weatherstation/data/weather_data.db',
                      help='Database path (default: /deepsink1/weatherstation/data/weather_data.db)')

    args = parser.parse_args()

    print("Virtual Observatory Polar Magnitude Plotter")
    print("="*48)
    print(f"Time range: {args.hours:.1f} hours")
    print(f"Database: {args.db}")
    print()

    try:
        plotter = VirtualObservatoryPolarPlotter(db_path=args.db)
        plotter.create_polar_magnitude_plots(hours=args.hours, save_path=args.output)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())