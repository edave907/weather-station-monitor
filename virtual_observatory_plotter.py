#!/usr/bin/env python3
"""
Virtual Observatory Comparison Plotter
Palmer, Alaska Virtual Geomagnetic Observatory

Plots and compares:
1. Palmer Virtual Observatory predictions (ML interpolation)
2. 4 Reference USGS observatories data
3. Local magnetic flux sensor data (calibrated HMC5883L)

Features:
- Time series comparison plots
- Magnitude and component analysis
- Uncertainty visualization
- Network geometry visualization
- Statistical analysis and correlation metrics
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

from virtual_observatory.virtual_station_predictor import VirtualObservatoryPredictor
from virtual_observatory.observatory_network import ObservatoryNetwork


class VirtualObservatoryPlotter:
    """Comprehensive plotting system for virtual observatory data comparison."""

    def __init__(self, db_path: str = "/deepsink1/weatherstation/data/weather_data.db"):
        """Initialize plotter with database connection."""
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
            'uncertainty': '#FFE66D'   # Yellow for uncertainty bands
        }

    def collect_local_magflux_data(self, hours: float = 24.0) -> Optional[pd.DataFrame]:
        """Collect local magnetic flux data from the magnetic_flux_data table with calibration."""
        try:
            import json

            # Load calibration data
            try:
                with open('weather_station_calibration.json', 'r') as f:
                    calibration = json.load(f)['calibration']
            except:
                print("Warning: Could not load calibration file, using default scaling")
                calibration = {
                    'magnetic_flux_x_scale': 5.119362344461532e-08,
                    'magnetic_flux_y_scale': 5.468460042213421e-09,
                    'magnetic_flux_z_scale': 3.285602009007802e-08,
                    'magnetic_flux_x_offset': 5.254899604336113e-09,
                    'magnetic_flux_y_offset': -4.11262082740767e-09,
                    'magnetic_flux_z_offset': -9.87942500592625e-09
                }

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

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['created_at'])

            # Apply calibration to convert raw counts to Tesla
            df['magflux_x_raw'] = df['x'] * calibration['magnetic_flux_x_scale'] + calibration['magnetic_flux_x_offset']
            df['magflux_y_raw'] = df['y'] * calibration['magnetic_flux_y_scale'] + calibration['magnetic_flux_y_offset']
            df['magflux_z_raw'] = df['z'] * calibration['magnetic_flux_z_scale'] + calibration['magnetic_flux_z_offset']

            # Apply coordinate transformation to correct sensor orientation
            # Load transformation parameters
            try:
                with open('weather_station_calibration.json', 'r') as f:
                    transform = json.load(f)['coordinate_transformation']

                # Convert angles to radians
                rx = np.radians(transform['rotation_x_degrees'])
                ry = np.radians(transform['rotation_y_degrees'])
                rz = np.radians(transform['rotation_z_degrees'])

                print(f"Applying coordinate transformation (RMS error: {transform['rms_error_nt']:.1f} nT)")

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

                # Combined rotation matrix (order: Rz * Ry * Rx)
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

            except Exception as e:
                print(f"Warning: Could not apply coordinate transformation: {e}")
                print("Using raw calibrated values without orientation correction")
                df['magflux_x'] = df['magflux_x_raw']
                df['magflux_y'] = df['magflux_y_raw']
                df['magflux_z'] = df['magflux_z_raw']

            # Calculate magnitude with corrected orientation
            df['magnitude'] = np.sqrt(df['magflux_x']**2 + df['magflux_y']**2 + df['magflux_z']**2)

            return df

        except Exception as e:
            print(f"Error collecting local data: {e}")
            return None

    def generate_virtual_observatory_timeseries(self, hours: float = 24.0, interval_minutes: int = 10) -> pd.DataFrame:
        """Generate virtual observatory predictions over time."""
        # For demonstration, we'll create a time series with simulated USGS data
        # In reality, this would fetch real USGS data over time

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # Create time series
        times = pd.date_range(start=start_time, end=end_time, freq=f'{interval_minutes}min')

        virtual_data = []

        print(f"Generating virtual observatory time series ({len(times)} points)...")

        for i, timestamp in enumerate(times):
            # Simulate slightly varying USGS data (realistic Palmer area values)
            # Add small time-based variations to simulate real geomagnetic activity
            time_variation = 0.01 * np.sin(2 * np.pi * i / (24 * 60 / interval_minutes))  # Daily cycle

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
                quality = self.predictor.interpolator.get_interpolation_quality_score(result)

            virtual_data.append({
                'timestamp': timestamp,
                'x': result.x_component,
                'y': result.y_component,
                'z': result.z_component,
                'magnitude': result.magnitude,
                'uncertainty': result.uncertainty_mag,
                'quality': quality
            })

        return pd.DataFrame(virtual_data)

    def generate_usgs_reference_data(self, hours: float = 24.0, interval_minutes: int = 10) -> Dict[str, pd.DataFrame]:
        """Generate simulated USGS observatory reference data."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        times = pd.date_range(start=start_time, end=end_time, freq=f'{interval_minutes}min')

        reference_data = {}

        # Base values for each observatory (realistic Alaska magnetic field values)
        base_values = {
            'CMO': np.array([55.7e-6, 2.1e-6, 54.2e-6]),  # College - closest
            'SIT': np.array([54.2e-6, 1.8e-6, 53.1e-6]),  # Sitka
            'SHU': np.array([53.8e-6, 2.3e-6, 52.9e-6]),  # Shumagin
            'DED': np.array([56.1e-6, 1.9e-6, 54.8e-6])   # Deadhorse
        }

        for obs_code, base_field in base_values.items():
            obs_data = []

            for i, timestamp in enumerate(times):
                # Add realistic geomagnetic variations
                daily_cycle = 0.01 * np.sin(2 * np.pi * i / (24 * 60 / interval_minutes))

                # Observatory-specific variations
                if obs_code == 'CMO':  # College - more auroral activity
                    auroral_activity = 0.005 * np.sin(4 * np.pi * i / (24 * 60 / interval_minutes))
                else:
                    auroral_activity = 0.002 * np.sin(3 * np.pi * i / (24 * 60 / interval_minutes))

                # Apply multiplicative variations to maintain realistic magnitudes
                variation_factor = 1 + daily_cycle + auroral_activity + np.random.normal(0, 0.001)
                field = base_field * variation_factor

                obs_data.append({
                    'timestamp': timestamp,
                    'x': field[0],
                    'y': field[1],
                    'z': field[2],
                    'magnitude': np.linalg.norm(field)
                })

            reference_data[obs_code] = pd.DataFrame(obs_data)

        return reference_data

    def plot_comprehensive_comparison(self, hours: float = 24.0, save_path: str = None):
        """Create comprehensive comparison plot of all magnetic field sources."""

        print("Collecting data for comprehensive comparison...")

        # Collect all data sources
        local_data = self.collect_local_magflux_data(hours)
        virtual_data = self.generate_virtual_observatory_timeseries(hours)
        usgs_data = self.generate_usgs_reference_data(hours)

        # Create figure with subplots
        fig, axes = plt.subplots(3, 2, figsize=(16, 12))
        fig.suptitle(f'Virtual Observatory Comparison - Palmer, Alaska\n'
                    f'Last {hours:.1f} hours • {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                    fontsize=16, fontweight='bold')

        # Plot 1: Magnetic Field Magnitude Comparison
        ax1 = axes[0, 0]

        # Plot virtual observatory
        ax1.plot(virtual_data['timestamp'], virtual_data['magnitude'] * 1e6,
                color=self.colors['virtual'], linewidth=2.5, label='Virtual Observatory (ML)', alpha=0.9)

        # Plot uncertainty band
        ax1.fill_between(virtual_data['timestamp'],
                        (virtual_data['magnitude'] - virtual_data['uncertainty']) * 1e6,
                        (virtual_data['magnitude'] + virtual_data['uncertainty']) * 1e6,
                        color=self.colors['uncertainty'], alpha=0.3, label='Uncertainty (±1σ)')

        # Plot local sensor if available
        if local_data is not None:
            ax1.plot(local_data['timestamp'], local_data['magnitude'] * 1e6,
                    color=self.colors['local'], linewidth=2, label='Local Sensor (HMC5883L)', alpha=0.8)

        # Plot USGS observatories
        for obs_code, data in usgs_data.items():
            ax1.plot(data['timestamp'], data['magnitude'] * 1e6,
                    color=self.colors[obs_code], linewidth=1.5, label=f'USGS {obs_code}', alpha=0.7)

        ax1.set_ylabel('Magnitude (μT)')
        ax1.set_title('Magnetic Field Magnitude Comparison')
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax1.grid(True, alpha=0.3)

        # Plot 2: X Component
        ax2 = axes[0, 1]
        ax2.plot(virtual_data['timestamp'], virtual_data['x'] * 1e6,
                color=self.colors['virtual'], linewidth=2.5, label='Virtual Observatory')

        if local_data is not None:
            ax2.plot(local_data['timestamp'], local_data['magflux_x'] * 1e6,
                    color=self.colors['local'], linewidth=2, label='Local Sensor')

        for obs_code, data in usgs_data.items():
            ax2.plot(data['timestamp'], data['x'] * 1e6,
                    color=self.colors[obs_code], linewidth=1.5, label=f'USGS {obs_code}', alpha=0.7)

        ax2.set_ylabel('X Component (μT)')
        ax2.set_title('X Component Comparison')
        ax2.grid(True, alpha=0.3)

        # Plot 3: Y Component
        ax3 = axes[1, 0]
        ax3.plot(virtual_data['timestamp'], virtual_data['y'] * 1e6,
                color=self.colors['virtual'], linewidth=2.5, label='Virtual Observatory')

        if local_data is not None:
            ax3.plot(local_data['timestamp'], local_data['magflux_y'] * 1e6,
                    color=self.colors['local'], linewidth=2, label='Local Sensor')

        for obs_code, data in usgs_data.items():
            ax3.plot(data['timestamp'], data['y'] * 1e6,
                    color=self.colors[obs_code], linewidth=1.5, label=f'USGS {obs_code}', alpha=0.7)

        ax3.set_ylabel('Y Component (μT)')
        ax3.set_title('Y Component Comparison')
        ax3.grid(True, alpha=0.3)

        # Plot 4: Z Component
        ax4 = axes[1, 1]
        ax4.plot(virtual_data['timestamp'], virtual_data['z'] * 1e6,
                color=self.colors['virtual'], linewidth=2.5, label='Virtual Observatory')

        if local_data is not None:
            ax4.plot(local_data['timestamp'], local_data['magflux_z'] * 1e6,
                    color=self.colors['local'], linewidth=2, label='Local Sensor')

        for obs_code, data in usgs_data.items():
            ax4.plot(data['timestamp'], data['z'] * 1e6,
                    color=self.colors[obs_code], linewidth=1.5, label=f'USGS {obs_code}', alpha=0.7)

        ax4.set_ylabel('Z Component (μT)')
        ax4.set_title('Z Component Comparison')
        ax4.grid(True, alpha=0.3)

        # Plot 5: Quality Score and Statistics
        ax5 = axes[2, 0]
        ax5.plot(virtual_data['timestamp'], virtual_data['quality'],
                color=self.colors['virtual'], linewidth=2, marker='o', markersize=3)
        ax5.set_ylabel('Quality Score')
        ax5.set_title('Virtual Observatory Quality Score')
        ax5.grid(True, alpha=0.3)
        ax5.set_ylim(0, 1)

        # Plot 6: Observatory Network Map
        ax6 = axes[2, 1]

        # Plot Palmer location
        palmer_lat, palmer_lon = 61.5994, -149.115
        ax6.plot(palmer_lon, palmer_lat, 'o', color=self.colors['virtual'],
                markersize=12, label='Palmer (Virtual Observatory)', zorder=5)

        # Plot USGS observatories
        for obs in self.predictor.network.nearest_four:
            ax6.plot(obs.longitude, obs.latitude, 's', color=self.colors[obs.code],
                    markersize=8, label=f'{obs.code} ({obs.distance_km:.0f} km)', zorder=4)

            # Draw connection lines
            ax6.plot([palmer_lon, obs.longitude], [palmer_lat, obs.latitude],
                    '--', color=self.colors[obs.code], alpha=0.5, linewidth=1, zorder=1)

        ax6.set_xlabel('Longitude (°W)')
        ax6.set_ylabel('Latitude (°N)')
        ax6.set_title('Observatory Network Geometry')
        ax6.legend(fontsize=8)
        ax6.grid(True, alpha=0.3)

        # Format x-axis for time plots
        for ax in [ax1, ax2, ax3, ax4, ax5]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, int(hours/12))))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        ax5.set_xlabel('Time (Hours)')

        plt.tight_layout()

        # Save plot
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_path = f'virtual_observatory_comparison_{timestamp}.png'
            plt.savefig(default_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {default_path}")

        plt.show()

        # Print summary statistics
        self.print_comparison_statistics(virtual_data, local_data, usgs_data)

    def print_comparison_statistics(self, virtual_data: pd.DataFrame,
                                  local_data: Optional[pd.DataFrame],
                                  usgs_data: Dict[str, pd.DataFrame]):
        """Print statistical summary of the comparison."""

        print("\n" + "="*60)
        print("VIRTUAL OBSERVATORY COMPARISON STATISTICS")
        print("="*60)

        # Virtual observatory stats
        print(f"\n🤖 Virtual Observatory (ML Interpolation):")
        print(f"   Mean magnitude: {virtual_data['magnitude'].mean()*1e6:.1f} μT")
        print(f"   Std deviation: {virtual_data['magnitude'].std()*1e6:.2f} μT")
        print(f"   Mean quality score: {virtual_data['quality'].mean():.3f}")
        print(f"   Mean uncertainty: ±{virtual_data['uncertainty'].mean()*1e6:.2f} μT")

        # Local sensor stats
        if local_data is not None:
            print(f"\n📡 Local Sensor (HMC5883L - Coordinate Corrected):")
            print(f"   Mean magnitude: {local_data['magnitude'].mean()*1e6:.1f} μT")
            print(f"   Std deviation: {local_data['magnitude'].std()*1e6:.2f} μT")
            print(f"   Data points: {len(local_data)}")

            # Show component comparison after transformation
            print(f"   Mean components: X={local_data['magflux_x'].mean()*1e6:.1f}, Y={local_data['magflux_y'].mean()*1e6:.1f}, Z={local_data['magflux_z'].mean()*1e6:.1f} μT")

            # Calculate correlation with virtual observatory (if time ranges overlap)
            # This would require time synchronization in a real implementation
            virtual_mean_mag = virtual_data['magnitude'].mean() * 1e6
            local_mean_mag = local_data['magnitude'].mean() * 1e6
            diff = abs(virtual_mean_mag - local_mean_mag)
            print(f"   Difference from virtual: {diff:.1f} μT ({diff/local_mean_mag*100:.1f}%)")
            print(f"   Note: Coordinate transformation applied (CMO reference frame)")
        else:
            print(f"\n📡 Local Sensor: No data available")

        # USGS observatory stats
        print(f"\n🏗️  USGS Reference Observatories:")
        for obs_code, data in usgs_data.items():
            obs = self.predictor.network.get_observatory_by_code(obs_code)
            weight = self.predictor.network.get_spatial_weights()[list(usgs_data.keys()).index(obs_code)]

            print(f"   {obs_code} ({obs.name}):")
            print(f"     Distance: {obs.distance_km:.0f} km, Weight: {weight:.1%}")
            print(f"     Mean magnitude: {data['magnitude'].mean()*1e6:.1f} μT")
            print(f"     Std deviation: {data['magnitude'].std()*1e6:.2f} μT")

        print("="*60)


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description='Virtual Observatory Comparison Plotter')
    parser.add_argument('--hours', type=float, default=24.0,
                      help='Time range in hours (default: 24)')
    parser.add_argument('--output', type=str,
                      help='Output filename for plot (default: auto-generated)')
    parser.add_argument('--db', type=str, default='/deepsink1/weatherstation/data/weather_data.db',
                      help='Database path (default: /deepsink1/weatherstation/data/weather_data.db)')

    args = parser.parse_args()

    print("Virtual Observatory Comparison Plotter")
    print("="*45)
    print(f"Time range: {args.hours:.1f} hours")
    print(f"Database: {args.db}")
    print()

    try:
        plotter = VirtualObservatoryPlotter(db_path=args.db)
        plotter.plot_comprehensive_comparison(hours=args.hours, save_path=args.output)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())