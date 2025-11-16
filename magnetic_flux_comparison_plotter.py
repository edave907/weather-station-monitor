#!/usr/bin/env python3
"""
Magnetic Flux Comparison Plotter

Enhanced 3D visualization utility that compares local HMC5883L magnetic flux data
with USGS geomagnetic observatory reference data for validation and analysis.

Features:
- Side-by-side comparison of local vs USGS data
- Difference analysis and correlation plots
- Automatic unit conversion (Tesla to microtesla for display)
- Time-synchronized data alignment
- Statistical comparison metrics
- NIST SP 330 compliant calibration for local data
- Observatory location context

Usage:
    python magnetic_flux_comparison_plotter.py --hours 24 --observatory BOU
    python magnetic_flux_comparison_plotter.py --start "2025-10-01" --end "2025-10-02" --observatory FRD
    python magnetic_flux_comparison_plotter.py --hours 6 --observatory TUC --save

Examples:
    # Compare last 24 hours with Boulder observatory
    python magnetic_flux_comparison_plotter.py --hours 24 --observatory BOU

    # Detailed analysis with difference plots
    python magnetic_flux_comparison_plotter.py --hours 12 --observatory FRD --plots all

    # Save comparison plots for specific date range
    python magnetic_flux_comparison_plotter.py --start "2025-10-03 10:00" --end "2025-10-03 18:00" --observatory BOU --save
"""

import argparse
import sqlite3
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os
import json
from scipy import stats
import sys

class MagneticFluxComparisonPlotter:
    """Compares local magnetic flux data with USGS observatory reference data."""

    def __init__(self, db_path: str = "weather_data.db"):
        self.db_path = db_path
        self.calibration_values = self.load_calibration()

        # Observatory information for context
        self.observatories = {
            'BOU': 'Boulder, Colorado',
            'FRD': 'Fredericksburg, Virginia',
            'TUC': 'Tucson, Arizona',
            'HON': 'Honolulu, Hawaii',
            'SJG': 'San Juan, Puerto Rico'
        }

    def load_calibration(self):
        """Load calibration values from JSON file."""
        calibration_file = "weather_station_calibration.json"
        default_calibration = {
            'magnetic_flux_x_scale': 9.174e-8,      # Tesla per LSb (HMC5883L datasheet)
            'magnetic_flux_y_scale': 9.174e-8,      # Tesla per LSb
            'magnetic_flux_z_scale': 9.174e-8,      # Tesla per LSb
            'magnetic_flux_x_offset': 0.0,          # Tesla offset
            'magnetic_flux_y_offset': 0.0,          # Tesla offset
            'magnetic_flux_z_offset': 0.0,          # Tesla offset
        }

        try:
            with open(calibration_file, 'r') as f:
                data = json.load(f)
                # Try both old and new calibration formats
                calibration = data.get('calibration_values', data.get('calibration', default_calibration))
                print(f"Loaded calibration from {calibration_file}")
                return calibration
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            print(f"Using default HMC5883L calibration values (9.174e-8 T/LSb)")
            return default_calibration

    def load_local_data(self, start_time: datetime, end_time: datetime, sample_interval: int = None):
        """Load local HMC5883L magnetic flux data and apply calibration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build query with optional sampling
            if sample_interval and sample_interval > 1:
                query = """
                    SELECT x, y, z, created_at
                    FROM (
                        SELECT *, ROW_NUMBER() OVER (ORDER BY created_at) as rn
                        FROM magnetic_flux_data
                        WHERE created_at BETWEEN ? AND ?
                    )
                    WHERE rn % ? = 1
                    ORDER BY created_at ASC
                """
                params = (start_time, end_time, sample_interval)
            else:
                query = """
                    SELECT x, y, z, created_at
                    FROM magnetic_flux_data
                    WHERE created_at BETWEEN ? AND ?
                    ORDER BY created_at ASC
                """
                params = (start_time, end_time)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                print("No local magnetic flux data found in specified time range")
                return None

            # Parse data
            times = []
            x_values = []
            y_values = []
            z_values = []

            for row in rows:
                x, y, z, timestamp_str = row
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', ''))
                times.append(timestamp)
                x_values.append(float(x))
                y_values.append(float(y))
                z_values.append(float(z))

            # Convert to numpy arrays
            times = np.array(times)
            x_raw = np.array(x_values)
            y_raw = np.array(y_values)
            z_raw = np.array(z_values)

            # Apply calibration to convert raw LSb values to Tesla
            x_array = (x_raw * self.calibration_values['magnetic_flux_x_scale']) + self.calibration_values['magnetic_flux_x_offset']
            y_array = (y_raw * self.calibration_values['magnetic_flux_y_scale']) + self.calibration_values['magnetic_flux_y_offset']
            z_array = (z_raw * self.calibration_values['magnetic_flux_z_scale']) + self.calibration_values['magnetic_flux_z_offset']

            magnitude = np.sqrt(x_array**2 + y_array**2 + z_array**2)

            print(f"Loaded {len(x_array)} local data points")
            print(f"Local calibrated range: X=[{x_array.min():.2e}, {x_array.max():.2e}] Tesla")

            return {
                'times': times,
                'x': x_array,
                'y': y_array,
                'z': z_array,
                'magnitude': magnitude,
                'source': 'Local HMC5883L'
            }

        except Exception as e:
            print(f"Error loading local data: {e}")
            return None

    def load_usgs_data(self, observatory_code: str, start_time: datetime, end_time: datetime, sample_interval: int = None):
        """Load USGS magnetic observatory data."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if USGS data exists
            cursor.execute("SELECT COUNT(*) FROM usgs_magnetic_data WHERE observatory_code = ?", (observatory_code,))
            if cursor.fetchone()[0] == 0:
                print(f"No USGS data found for observatory {observatory_code}")
                print("Run usgs_magnetic_importer.py first to import reference data")
                conn.close()
                return None

            # Build query with optional sampling
            if sample_interval and sample_interval > 1:
                query = """
                    SELECT x, y, z, f, data_timestamp
                    FROM (
                        SELECT *, ROW_NUMBER() OVER (ORDER BY data_timestamp) as rn
                        FROM usgs_magnetic_data
                        WHERE observatory_code = ? AND data_timestamp BETWEEN ? AND ?
                    )
                    WHERE rn % ? = 1
                    ORDER BY data_timestamp ASC
                """
                params = (observatory_code, start_time, end_time, sample_interval)
            else:
                query = """
                    SELECT x, y, z, f, data_timestamp
                    FROM usgs_magnetic_data
                    WHERE observatory_code = ? AND data_timestamp BETWEEN ? AND ?
                    ORDER BY data_timestamp ASC
                """
                params = (observatory_code, start_time, end_time)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                print(f"No USGS data found for {observatory_code} in specified time range")
                return None

            # Parse data (already in Tesla units)
            times = []
            x_values = []
            y_values = []
            z_values = []
            f_values = []

            for row in rows:
                x, y, z, f, timestamp_str = row
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', ''))
                times.append(timestamp)
                x_values.append(float(x))
                y_values.append(float(y))
                z_values.append(float(z))
                if f is not None:
                    f_values.append(float(f))

            # Convert to numpy arrays
            times = np.array(times)
            x_array = np.array(x_values)
            y_array = np.array(y_values)
            z_array = np.array(z_values)
            f_array = np.array(f_values) if f_values else None

            magnitude = np.sqrt(x_array**2 + y_array**2 + z_array**2)

            observatory_name = self.observatories.get(observatory_code, observatory_code)
            print(f"Loaded {len(x_array)} USGS data points from {observatory_name}")
            print(f"USGS range: X=[{x_array.min():.2e}, {x_array.max():.2e}] Tesla")

            return {
                'times': times,
                'x': x_array,
                'y': y_array,
                'z': z_array,
                'f': f_array,
                'magnitude': magnitude,
                'source': f'USGS {observatory_code} ({observatory_name})',
                'observatory': observatory_code
            }

        except Exception as e:
            print(f"Error loading USGS data: {e}")
            return None

    def align_time_series(self, local_data, usgs_data, tolerance_minutes=5):
        """Align local and USGS data by timestamp with tolerance."""
        if not local_data or not usgs_data:
            return None, None

        tolerance = timedelta(minutes=tolerance_minutes)

        aligned_local = {'times': [], 'x': [], 'y': [], 'z': [], 'magnitude': []}
        aligned_usgs = {'times': [], 'x': [], 'y': [], 'z': [], 'magnitude': []}

        # Convert all timestamps to timezone-naive for comparison
        local_times_naive = []
        for t in local_data['times']:
            if hasattr(t, 'tzinfo') and t.tzinfo is not None:
                local_times_naive.append(t.replace(tzinfo=None))
            else:
                local_times_naive.append(t)

        usgs_times_naive = []
        for t in usgs_data['times']:
            if hasattr(t, 'tzinfo') and t.tzinfo is not None:
                usgs_times_naive.append(t.replace(tzinfo=None))
            else:
                usgs_times_naive.append(t)

        usgs_times_naive = np.array(usgs_times_naive)

        for i, local_time in enumerate(local_times_naive):
            # Find closest USGS time within tolerance
            time_diffs = np.abs(usgs_times_naive - local_time)
            min_diff_idx = np.argmin(time_diffs)

            if time_diffs[min_diff_idx] <= tolerance:
                aligned_local['times'].append(local_time)
                aligned_local['x'].append(local_data['x'][i])
                aligned_local['y'].append(local_data['y'][i])
                aligned_local['z'].append(local_data['z'][i])
                aligned_local['magnitude'].append(local_data['magnitude'][i])

                aligned_usgs['times'].append(usgs_data['times'][min_diff_idx])
                aligned_usgs['x'].append(usgs_data['x'][min_diff_idx])
                aligned_usgs['y'].append(usgs_data['y'][min_diff_idx])
                aligned_usgs['z'].append(usgs_data['z'][min_diff_idx])
                aligned_usgs['magnitude'].append(usgs_data['magnitude'][min_diff_idx])

        # Convert to numpy arrays
        for key in ['x', 'y', 'z', 'magnitude']:
            aligned_local[key] = np.array(aligned_local[key])
            aligned_usgs[key] = np.array(aligned_usgs[key])

        aligned_local['times'] = np.array(aligned_local['times'])
        aligned_usgs['times'] = np.array(aligned_usgs['times'])

        # Preserve source labels
        aligned_local['source'] = local_data['source']
        aligned_usgs['source'] = usgs_data['source']

        print(f"Aligned {len(aligned_local['times'])} data points within {tolerance_minutes} minute tolerance")

        if len(aligned_local['times']) == 0:
            print("Warning: No overlapping data points found within time tolerance")
            return None, None

        return aligned_local, aligned_usgs

    def calculate_statistics(self, local_data, usgs_data):
        """Calculate comparison statistics between local and USGS data."""
        if not local_data or not usgs_data:
            return None

        stats_dict = {}

        for component in ['x', 'y', 'z', 'magnitude']:
            local_vals = local_data[component] * 1e6  # Convert to microtesla
            usgs_vals = usgs_data[component] * 1e6    # Convert to microtesla

            # Calculate differences
            diff = local_vals - usgs_vals

            # Basic statistics
            stats_dict[component] = {
                'local_mean': np.mean(local_vals),
                'usgs_mean': np.mean(usgs_vals),
                'local_std': np.std(local_vals),
                'usgs_std': np.std(usgs_vals),
                'diff_mean': np.mean(diff),
                'diff_std': np.std(diff),
                'diff_rms': np.sqrt(np.mean(diff**2)),
                'correlation': np.corrcoef(local_vals, usgs_vals)[0, 1] if len(local_vals) > 1 else 0
            }

        return stats_dict

    def create_comparison_plot(self, local_data, usgs_data, title_suffix=""):
        """Create side-by-side comparison plots."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Magnetic Field Comparison {title_suffix}', fontsize=14, fontweight='bold')

        components = ['x', 'y', 'z', 'magnitude']
        component_names = ['X (North)', 'Y (East)', 'Z (Down)', 'Magnitude']

        for i, (comp, name) in enumerate(zip(components, component_names)):
            ax = axes[i//2, i%2]

            # Convert Tesla to microtesla for display
            local_vals = local_data[comp] * 1e6
            usgs_vals = usgs_data[comp] * 1e6

            ax.plot(local_data['times'], local_vals, 'b-', label=local_data['source'], alpha=0.7, linewidth=1)
            ax.plot(usgs_data['times'], usgs_vals, 'r-', label=usgs_data['source'], alpha=0.7, linewidth=1)

            ax.set_title(f'{name} Component')
            ax.set_ylabel('Magnetic Field (μT)')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, len(local_data['times'])//10)))

            # Rotate labels if needed
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        return fig

    def create_difference_plot(self, local_data, usgs_data, title_suffix=""):
        """Create plots showing differences between local and USGS data."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Local vs USGS Differences {title_suffix}', fontsize=14, fontweight='bold')

        components = ['x', 'y', 'z', 'magnitude']
        component_names = ['X (North)', 'Y (East)', 'Z (Down)', 'Magnitude']

        for i, (comp, name) in enumerate(zip(components, component_names)):
            ax = axes[i//2, i%2]

            # Calculate differences in microtesla
            local_vals = local_data[comp] * 1e6
            usgs_vals = usgs_data[comp] * 1e6
            diff = local_vals - usgs_vals

            ax.plot(local_data['times'], diff, 'g-', alpha=0.7, linewidth=1)
            ax.axhline(y=0, color='k', linestyle='--', alpha=0.5)

            # Add statistics text
            rms_diff = np.sqrt(np.mean(diff**2))
            mean_diff = np.mean(diff)
            std_diff = np.std(diff)

            stats_text = f'RMS: {rms_diff:.2f} μT\nMean: {mean_diff:.2f} μT\nStd: {std_diff:.2f} μT'
            ax.text(0.05, 0.95, stats_text, transform=ax.transAxes,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

            ax.set_title(f'{name} Difference (Local - USGS)')
            ax.set_ylabel('Difference (μT)')
            ax.grid(True, alpha=0.3)

            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, len(local_data['times'])//10)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        return fig

    def create_correlation_plot(self, local_data, usgs_data, title_suffix=""):
        """Create correlation scatter plots."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Local vs USGS Correlation {title_suffix}', fontsize=14, fontweight='bold')

        components = ['x', 'y', 'z', 'magnitude']
        component_names = ['X (North)', 'Y (East)', 'Z (Down)', 'Magnitude']

        for i, (comp, name) in enumerate(zip(components, component_names)):
            ax = axes[i//2, i%2]

            # Convert to microtesla
            local_vals = local_data[comp] * 1e6
            usgs_vals = usgs_data[comp] * 1e6

            ax.scatter(usgs_vals, local_vals, alpha=0.6, s=10)

            # Add perfect correlation line
            min_val = min(np.min(local_vals), np.min(usgs_vals))
            max_val = max(np.max(local_vals), np.max(usgs_vals))
            ax.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8, label='Perfect correlation')

            # Calculate and display correlation coefficient
            if len(local_vals) > 1:
                corr_coef = np.corrcoef(local_vals, usgs_vals)[0, 1]
                ax.text(0.05, 0.95, f'r = {corr_coef:.3f}', transform=ax.transAxes,
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

            ax.set_xlabel(f'USGS {name} (μT)')
            ax.set_ylabel(f'Local {name} (μT)')
            ax.set_title(f'{name} Correlation')
            ax.grid(True, alpha=0.3)
            ax.legend()

        plt.tight_layout()
        return fig

    def print_statistics_summary(self, stats):
        """Print comprehensive statistics summary."""
        if not stats:
            return

        print("\n" + "="*80)
        print("MAGNETIC FIELD COMPARISON STATISTICS")
        print("="*80)

        components = ['x', 'y', 'z', 'magnitude']
        component_names = ['X (North)', 'Y (East)', 'Z (Down)', 'Magnitude']

        for comp, name in zip(components, component_names):
            s = stats[comp]
            print(f"\n{name} Component:")
            print(f"  Local Mean:    {s['local_mean']:8.2f} μT  (Std: {s['local_std']:6.2f} μT)")
            print(f"  USGS Mean:     {s['usgs_mean']:8.2f} μT  (Std: {s['usgs_std']:6.2f} μT)")
            print(f"  Difference:    {s['diff_mean']:8.2f} μT  (RMS: {s['diff_rms']:6.2f} μT)")
            print(f"  Correlation:   {s['correlation']:8.3f}")

        print("\n" + "="*80)

def main():
    parser = argparse.ArgumentParser(description='Compare local magnetic flux data with USGS observatory data')
    parser.add_argument('--observatory', '-o', required=True, help='USGS observatory code (BOU, FRD, TUC, HON, SJG)')
    parser.add_argument('--start', help='Start time (YYYY-MM-DD or "YYYY-MM-DD HH:MM")')
    parser.add_argument('--end', help='End time (YYYY-MM-DD or "YYYY-MM-DD HH:MM")')
    parser.add_argument('--hours', type=int, help='Hours of recent data to compare')
    parser.add_argument('--days', type=int, help='Days of recent data to compare')
    parser.add_argument('--db', default='weather_data.db', help='Database path')
    parser.add_argument('--plots', choices=['comparison', 'difference', 'correlation', 'all'],
                        default='comparison', help='Plot types to generate')
    parser.add_argument('--save', action='store_true', help='Save plots to files')
    parser.add_argument('--output-dir', default='comparison_plots', help='Output directory for saved plots')
    parser.add_argument('--tolerance', type=int, default=5, help='Time alignment tolerance in minutes')

    args = parser.parse_args()

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
            return
    else:
        start_time = end_time - timedelta(hours=24)
        print("No time range specified, using last 24 hours")

    print(f"Comparing magnetic flux data: {start_time} to {end_time}")
    print(f"Observatory: {args.observatory}")

    # Create plotter and load data
    plotter = MagneticFluxComparisonPlotter(args.db)

    # Determine sampling for large datasets
    time_span = end_time - start_time
    estimated_points = int(time_span.total_seconds() / 5)  # Assuming 5-second intervals
    max_points = 2000
    sample_interval = max(1, estimated_points // max_points) if estimated_points > max_points else None

    if sample_interval:
        print(f"Using data sampling (every {sample_interval} points) for performance")

    local_data = plotter.load_local_data(start_time, end_time, sample_interval)
    usgs_data = plotter.load_usgs_data(args.observatory, start_time, end_time, sample_interval)

    if not local_data:
        print("No local magnetic flux data available. Check your database and time range.")
        return

    if not usgs_data:
        print(f"No USGS data available for {args.observatory}. Run usgs_magnetic_importer.py first.")
        return

    # Align time series
    aligned_local, aligned_usgs = plotter.align_time_series(local_data, usgs_data, args.tolerance)

    if not aligned_local or not aligned_usgs:
        print("No overlapping data found. Check time ranges and try increasing tolerance.")
        return

    # Calculate statistics
    stats = plotter.calculate_statistics(aligned_local, aligned_usgs)
    plotter.print_statistics_summary(stats)

    # Create plots
    title_suffix = f"({start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')})"
    figures = []

    if args.plots in ['comparison', 'all']:
        fig = plotter.create_comparison_plot(aligned_local, aligned_usgs, title_suffix)
        figures.append(('comparison', fig))

    if args.plots in ['difference', 'all']:
        fig = plotter.create_difference_plot(aligned_local, aligned_usgs, title_suffix)
        figures.append(('difference', fig))

    if args.plots in ['correlation', 'all']:
        fig = plotter.create_correlation_plot(aligned_local, aligned_usgs, title_suffix)
        figures.append(('correlation', fig))

    # Save plots if requested
    if args.save:
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        for plot_type, fig in figures:
            filename = f"{args.output_dir}/magnetic_comparison_{plot_type}_{args.observatory}_{timestamp}.png"
            fig.savefig(filename, dpi=150, bbox_inches='tight')
            print(f"Saved {plot_type} plot: {filename}")

    # Show plots if not saving
    if not args.save:
        plt.show()

if __name__ == "__main__":
    main()