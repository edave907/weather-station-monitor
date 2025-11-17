#!/usr/bin/env python3
"""
Magnetic Flux 3D Visualization Utility

This utility reads magnetic flux data from the weather station database
and creates 3D plots showing magnitude and direction over time.

Features:
- 3D vector field visualization
- Magnitude vs time plots
- Direction analysis (declination/inclination)
- 2D polar plots for XY plane analysis
- Interactive 3D plots
- Time range selection
- NIST SP 330 compliant units (Tesla, converted from HMC5883L LSb values)
- Automatic calibration loading from weather_station_calibration.json

Calibration:
The plotter automatically loads calibration values from weather_station_calibration.json
to convert raw HMC5883L LSb values to Tesla units according to NIST SP 330 standards.
Default: 9.174e-8 T/LSb (based on HMC5883L datasheet: 1090 LSb/Gauss)

Usage:
    python magnetic_flux_3d_plotter.py [options]

Examples:
    # Plot last 24 hours with calibrated data
    python magnetic_flux_3d_plotter.py --hours 24

    # Create 2D polar plot
    python magnetic_flux_3d_plotter.py --hours 6 --plots polar

    # Plot specific date range
    python magnetic_flux_3d_plotter.py --start "2025-10-03 10:00" --end "2025-10-03 18:00"

    # Save calibrated plots to files
    python magnetic_flux_3d_plotter.py --save --output-dir plots/
"""

import argparse
import sqlite3
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os
import sys
import json

# Add project directory to path for database import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database import WeatherDatabase
except ImportError:
    print("Error: Could not import WeatherDatabase. Make sure database.py is in the same directory.")
    sys.exit(1)


class MagneticFlux3DPlotter:
    """3D visualization utility for magnetic flux data."""

    def __init__(self, db_path="weather_data.db", calibration_file="weather_station_calibration.json"):
        """Initialize the plotter with database connection and calibration."""
        self.db_path = db_path
        self.database = WeatherDatabase(db_path)
        self.calibration_file = calibration_file

        # Load calibration values
        self.calibration_values = self.load_calibration_values()

        print(f"Using magnetic flux calibration:")
        print(f"  X scale: {self.calibration_values['magnetic_flux_x_scale']:.3e} T/LSb")
        print(f"  Y scale: {self.calibration_values['magnetic_flux_y_scale']:.3e} T/LSb")
        print(f"  Z scale: {self.calibration_values['magnetic_flux_z_scale']:.3e} T/LSb")

    def load_calibration_values(self):
        """Load calibration values from file or use defaults."""
        # Default calibration values (NIST SP 330 - SI Units)
        default_calibration_values = {
            # HMC5883L Magnetic Flux Sensor (NIST SP 330 - Tesla SI unit)
            'magnetic_flux_x_scale': 9.174e-8,      # Tesla per LSb (1/(1090 LSb/Gauss * 10000 Gauss/Tesla))
            'magnetic_flux_y_scale': 9.174e-8,      # Tesla per LSb
            'magnetic_flux_z_scale': 9.174e-8,      # Tesla per LSb
            'magnetic_flux_x_offset': 0.0,          # Tesla offset
            'magnetic_flux_y_offset': 0.0,          # Tesla offset
            'magnetic_flux_z_offset': 0.0           # Tesla offset
        }

        try:
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)

                # Extract calibration values (handle both old and new format)
                if 'calibration' in data:
                    loaded_values = data['calibration']
                else:
                    loaded_values = data  # Old format compatibility

                # Merge loaded values with defaults (in case new calibration parameters were added)
                calibration_values = default_calibration_values.copy()
                calibration_values.update(loaded_values)

                print(f"Loaded calibration values from {self.calibration_file}")
                return calibration_values
            else:
                print(f"No calibration file found, using defaults")
                return default_calibration_values.copy()

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading calibration file: {e}. Using defaults.")
            return default_calibration_values.copy()

    def get_magnetic_flux_data(self, start_time, end_time):
        """Retrieve magnetic flux data for the specified time range."""
        try:
            data = self.database.get_magnetic_flux_data_range(start_time, end_time)
            if not data:
                print(f"No magnetic flux data found between {start_time} and {end_time}")
                return None

            print(f"Retrieved {len(data)} magnetic flux records")
            return data

        except Exception as e:
            print(f"Error retrieving data: {e}")
            return None

    def process_data(self, raw_data):
        """Process raw database data into arrays for plotting."""
        if not raw_data:
            return None

        # Extract data into arrays
        times = []
        x_values = []
        y_values = []
        z_values = []

        for row in raw_data:
            # row format: (x, y, z, created_at)
            x, y, z, timestamp_str = row

            # Parse timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            times.append(timestamp)

            # Store raw magnetic field components (LSb values from HMC5883L)
            x_values.append(float(x))
            y_values.append(float(y))
            z_values.append(float(z))

        # Convert to numpy arrays
        times = np.array(times)
        x_raw = np.array(x_values)
        y_raw = np.array(y_values)
        z_raw = np.array(z_values)

        # Apply calibration to convert raw LSb values to Tesla (NIST SP 330 SI units)
        x_array = (x_raw * self.calibration_values['magnetic_flux_x_scale']) + self.calibration_values['magnetic_flux_x_offset']
        y_array = (y_raw * self.calibration_values['magnetic_flux_y_scale']) + self.calibration_values['magnetic_flux_y_offset']
        z_array = (z_raw * self.calibration_values['magnetic_flux_z_scale']) + self.calibration_values['magnetic_flux_z_offset']

        print(f"Applied calibration to {len(x_array)} data points")
        print(f"Raw range: X=[{x_raw.min():.0f}, {x_raw.max():.0f}] LSb")
        print(f"Calibrated range: X=[{x_array.min():.2e}, {x_array.max():.2e}] Tesla")

        # Calculate derived quantities
        magnitude = np.sqrt(x_array**2 + y_array**2 + z_array**2)

        # Calculate magnetic declination (angle from magnetic north)
        declination = np.degrees(np.arctan2(y_array, x_array))

        # Calculate magnetic inclination (dip angle)
        horizontal_component = np.sqrt(x_array**2 + y_array**2)
        inclination = np.degrees(np.arctan2(z_array, horizontal_component))

        return {
            'times': times,
            'x': x_array,
            'y': y_array,
            'z': z_array,
            'magnitude': magnitude,
            'declination': declination,
            'inclination': inclination
        }

    def create_3d_vector_plot(self, data, title="Magnetic Flux 3D Vectors"):
        """Create 3D vector field plot."""
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        # Convert Tesla to microtesla for better readability (1 T = 1e6 μT)
        x_microtesla = data['x'] * 1e6
        y_microtesla = data['y'] * 1e6
        z_microtesla = data['z'] * 1e6

        # Use time as the third dimension for vector positions
        time_numeric = mdates.date2num(data['times'])
        time_normalized = (time_numeric - time_numeric.min()) / (time_numeric.max() - time_numeric.min())

        # Sample data for cleaner visualization (every Nth point)
        n_points = len(data['x'])
        step = max(1, n_points // 50)  # Show max 50 vectors
        indices = range(0, n_points, step)

        # Create 3D quiver plot - use simple quiver without color argument
        quiver = ax.quiver(x_microtesla[indices],
                          y_microtesla[indices],
                          z_microtesla[indices],
                          x_microtesla[indices],
                          y_microtesla[indices],
                          z_microtesla[indices],
                          length=0.1, normalize=True,
                          color='blue', alpha=0.6)

        # Add scatter plot with time coloring
        scatter = ax.scatter(x_microtesla[indices], y_microtesla[indices], z_microtesla[indices],
                           c=time_normalized[indices], cmap='viridis', s=30, alpha=0.8)

        ax.set_xlabel('X Component (μT)')
        ax.set_ylabel('Y Component (μT)')
        ax.set_zlabel('Z Component (μT)')
        ax.set_title(f"{title} (NIST SP 330 Calibrated)")

        # Add colorbar for time
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.5, aspect=5)
        cbar.set_label('Time (normalized)')

        return fig

    def create_magnitude_time_plot(self, data, title="Magnetic Flux Magnitude vs Time"):
        """Create magnitude vs time plot."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # Convert Tesla to microtesla for better readability (1 T = 1e6 μT)
        magnitude_microtesla = data['magnitude'] * 1e6
        x_microtesla = data['x'] * 1e6
        y_microtesla = data['y'] * 1e6
        z_microtesla = data['z'] * 1e6

        # Magnitude plot
        ax1.plot(data['times'], magnitude_microtesla, 'b-', linewidth=1, alpha=0.8)
        ax1.set_ylabel('Magnitude (μT)')
        ax1.set_title(f"{title} (NIST SP 330 Calibrated)")
        ax1.grid(True, alpha=0.3)

        # Statistics
        mean_mag = np.mean(magnitude_microtesla)
        std_mag = np.std(magnitude_microtesla)
        ax1.axhline(mean_mag, color='r', linestyle='--', alpha=0.7,
                   label=f'Mean: {mean_mag:.2f} μT')
        ax1.fill_between(data['times'], mean_mag - std_mag, mean_mag + std_mag,
                        alpha=0.2, color='red', label=f'±1σ: {std_mag:.2f} μT')
        ax1.legend()

        # Components plot
        ax2.plot(data['times'], x_microtesla, 'r-', label='X Component', alpha=0.7)
        ax2.plot(data['times'], y_microtesla, 'g-', label='Y Component', alpha=0.7)
        ax2.plot(data['times'], z_microtesla, 'b-', label='Z Component', alpha=0.7)
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Component Value (μT)')
        ax2.set_title('Individual Components')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax2.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        plt.xticks(rotation=45)

        plt.tight_layout()
        return fig

    def create_direction_analysis_plot(self, data, title="Magnetic Field Direction Analysis"):
        """Create declination and inclination analysis plots."""
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

        # Declination (horizontal angle)
        ax1.plot(data['times'], data['declination'], 'purple', linewidth=1)
        ax1.set_ylabel('Declination (°)')
        ax1.set_title('Magnetic Declination (Angle from North)')
        ax1.grid(True, alpha=0.3)
        ax1.axhline(0, color='k', linestyle='-', alpha=0.3)

        # Inclination (dip angle)
        ax2.plot(data['times'], data['inclination'], 'orange', linewidth=1)
        ax2.set_ylabel('Inclination (°)')
        ax2.set_title('Magnetic Inclination (Dip Angle)')
        ax2.grid(True, alpha=0.3)
        ax2.axhline(0, color='k', linestyle='-', alpha=0.3)

        # Horizontal component
        horizontal = np.sqrt(data['x']**2 + data['y']**2)
        ax3.plot(data['times'], horizontal, 'cyan', label='Horizontal', linewidth=1)
        ax3.plot(data['times'], np.abs(data['z']), 'brown', label='Vertical (|Z|)', linewidth=1)
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Component Magnitude (μT)')
        ax3.set_title('Horizontal vs Vertical Components')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Format x-axis
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax3.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        plt.xticks(rotation=45)

        plt.tight_layout()
        return fig

    def create_3d_trajectory_plot(self, data, title="Magnetic Field Trajectory"):
        """Create 3D trajectory plot showing how the magnetic field vector moves over time."""
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        # Create trajectory line
        time_numeric = mdates.date2num(data['times'])
        time_normalized = (time_numeric - time_numeric.min()) / (time_numeric.max() - time_numeric.min())

        # Plot trajectory
        ax.plot(data['x'], data['y'], data['z'], 'b-', alpha=0.6, linewidth=1)

        # Color points by time
        scatter = ax.scatter(data['x'], data['y'], data['z'],
                           c=time_normalized, cmap='plasma', s=20, alpha=0.8)

        # Mark start and end points
        ax.scatter(data['x'][0], data['y'][0], data['z'][0],
                  c='green', s=100, marker='o', label='Start')
        ax.scatter(data['x'][-1], data['y'][-1], data['z'][-1],
                  c='red', s=100, marker='s', label='End')

        ax.set_xlabel('X Component (μT)')
        ax.set_ylabel('Y Component (μT)')
        ax.set_zlabel('Z Component (μT)')
        ax.set_title(title)
        ax.legend()

        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.5, aspect=5)
        cbar.set_label('Time Progress')

        return fig

    def create_2d_polar_plot(self, data, title="Magnetic Field XY Plane - Polar View"):
        """Create 2D polar plot showing magnitude and direction in XY plane."""
        fig = plt.figure(figsize=(12, 10))

        # Create polar subplot
        ax_polar = fig.add_subplot(221, projection='polar')

        # Convert Tesla to microtesla for better readability (1 T = 1e6 μT)
        x_microtesla = data['x'] * 1e6
        y_microtesla = data['y'] * 1e6

        # Calculate XY plane magnitude and angle
        xy_magnitude = np.sqrt(x_microtesla**2 + y_microtesla**2)
        xy_angle = np.arctan2(y_microtesla, x_microtesla)  # Angle in radians

        # Create time-based coloring
        time_numeric = mdates.date2num(data['times'])
        time_normalized = (time_numeric - time_numeric.min()) / (time_numeric.max() - time_numeric.min())

        # Polar scatter plot
        scatter = ax_polar.scatter(xy_angle, xy_magnitude, c=time_normalized,
                                 cmap='plasma', s=20, alpha=0.7)

        # Add trajectory line
        ax_polar.plot(xy_angle, xy_magnitude, 'b-', alpha=0.3, linewidth=0.5)

        ax_polar.set_title('XY Plane Polar View\n(Horizontal Magnetic Field - NIST SP 330)',
                          fontsize=12, pad=20)
        ax_polar.set_xlabel('Magnitude (μT)')
        ax_polar.set_theta_zero_location('N')  # North at top
        ax_polar.set_theta_direction(-1)  # Clockwise

        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax_polar, shrink=0.8, pad=0.1)
        cbar.set_label('Time Progress')

        # Create XY cartesian plot
        ax_xy = fig.add_subplot(222)
        scatter_xy = ax_xy.scatter(data['x'], data['y'], c=time_normalized,
                                  cmap='plasma', s=20, alpha=0.7)
        ax_xy.plot(data['x'], data['y'], 'b-', alpha=0.3, linewidth=0.5)
        ax_xy.set_xlabel('X Component (μT)')
        ax_xy.set_ylabel('Y Component (μT)')
        ax_xy.set_title('XY Cartesian View')
        ax_xy.grid(True, alpha=0.3)
        ax_xy.axis('equal')

        # Add center point and axes
        ax_xy.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        ax_xy.axvline(x=0, color='k', linestyle='-', alpha=0.3)

        # Magnitude vs Time plot
        ax_mag = fig.add_subplot(223)
        ax_mag.plot(data['times'], xy_magnitude, 'purple', linewidth=1, label='XY Magnitude')
        ax_mag.plot(data['times'], np.abs(data['z']), 'brown', linewidth=1, label='Z Magnitude')
        ax_mag.plot(data['times'], data['magnitude'], 'black', linewidth=1, label='Total Magnitude')
        ax_mag.set_xlabel('Time')
        ax_mag.set_ylabel('Magnitude (μT)')
        ax_mag.set_title('Magnitude Components vs Time')
        ax_mag.legend()
        ax_mag.grid(True, alpha=0.3)

        # Format time axis
        ax_mag.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax_mag.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        plt.setp(ax_mag.xaxis.get_majorticklabels(), rotation=45)

        # Angle vs Time plot
        ax_angle = fig.add_subplot(224)
        angle_degrees = np.degrees(xy_angle)
        # Unwrap angles to avoid discontinuities
        angle_unwrapped = np.degrees(np.unwrap(xy_angle))
        ax_angle.plot(data['times'], angle_degrees, 'green', linewidth=1, alpha=0.7, label='Raw Angle')
        ax_angle.plot(data['times'], angle_unwrapped, 'darkgreen', linewidth=1, label='Unwrapped Angle')
        ax_angle.set_xlabel('Time')
        ax_angle.set_ylabel('XY Angle (degrees)')
        ax_angle.set_title('XY Plane Angle vs Time')
        ax_angle.legend()
        ax_angle.grid(True, alpha=0.3)

        # Format time axis
        ax_angle.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax_angle.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        plt.setp(ax_angle.xaxis.get_majorticklabels(), rotation=45)

        plt.suptitle(title, fontsize=14)
        plt.tight_layout()

        return fig

    def print_statistics(self, data):
        """Print statistical summary of the magnetic flux data."""
        print("\n" + "="*60)
        print("MAGNETIC FLUX DATA STATISTICS")
        print("="*60)

        print(f"Time Range: {data['times'][0]} to {data['times'][-1]}")
        print(f"Duration: {data['times'][-1] - data['times'][0]}")
        print(f"Number of samples: {len(data['times'])}")

        print(f"\nMagnetic Field Components (μT):")
        print(f"  X: {np.mean(data['x'])*1e6:.2f} ± {np.std(data['x'])*1e6:.2f} (range: {np.min(data['x'])*1e6:.2f} to {np.max(data['x'])*1e6:.2f})")
        print(f"  Y: {np.mean(data['y'])*1e6:.2f} ± {np.std(data['y'])*1e6:.2f} (range: {np.min(data['y'])*1e6:.2f} to {np.max(data['y'])*1e6:.2f})")
        print(f"  Z: {np.mean(data['z'])*1e6:.2f} ± {np.std(data['z'])*1e6:.2f} (range: {np.min(data['z'])*1e6:.2f} to {np.max(data['z'])*1e6:.2f})")

        print(f"\nMagnetic Field Magnitude:")
        print(f"  Mean: {np.mean(data['magnitude'])*1e6:.2f} μT")
        print(f"  Std Dev: {np.std(data['magnitude'])*1e6:.2f} μT")
        print(f"  Range: {np.min(data['magnitude'])*1e6:.2f} to {np.max(data['magnitude'])*1e6:.2f} μT")

        print(f"\nMagnetic Field Direction:")
        print(f"  Declination: {np.mean(data['declination']):.1f}° ± {np.std(data['declination']):.1f}°")
        print(f"  Inclination: {np.mean(data['inclination']):.1f}° ± {np.std(data['inclination']):.1f}°")

        # Earth's magnetic field context
        earth_field_typical = 50  # μT (typical Earth's field strength)
        print(f"\nEarth's Magnetic Field Context:")
        print(f"  Typical Earth field: ~{earth_field_typical} μT")
        print(f"  Measured field ratio: {np.mean(data['magnitude'])*1e6/earth_field_typical:.2f}x typical")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="3D Magnetic Flux Visualization Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --hours 24                    # Last 24 hours
  %(prog)s --start "2025-10-03 10:00"    # From specific time to now
  %(prog)s --start "2025-10-03 10:00" --end "2025-10-03 18:00"  # Date range
  %(prog)s --save --output-dir plots/    # Save plots to directory
        """
    )

    parser.add_argument('--db', default='/deepsink1/weatherstation/data/weather_data.db',
                       help='Database file path (default: /deepsink1/weatherstation/data/weather_data.db)')

    # Time range options
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('--hours', type=float, default=24,
                           help='Hours of data to plot (default: 24)')
    time_group.add_argument('--days', type=float,
                           help='Days of data to plot')

    parser.add_argument('--start', type=str,
                       help='Start time (YYYY-MM-DD HH:MM format)')
    parser.add_argument('--end', type=str,
                       help='End time (YYYY-MM-DD HH:MM format)')

    # Output options
    parser.add_argument('--save', action='store_true',
                       help='Save plots to files instead of displaying')
    parser.add_argument('--output-dir', default='.',
                       help='Output directory for saved plots (default: current)')
    parser.add_argument('--format', choices=['png', 'pdf', 'svg'], default='png',
                       help='Output format for saved plots (default: png)')

    # Display options
    parser.add_argument('--no-stats', action='store_true',
                       help='Skip printing statistics')
    parser.add_argument('--plots', nargs='+',
                       choices=['vectors', 'magnitude', 'direction', 'trajectory', 'polar', 'all'],
                       default=['all'],
                       help='Which plots to create (default: all)')

    return parser.parse_args()


def main():
    """Main function."""
    args = parse_arguments()

    # Initialize plotter
    print("Initializing Magnetic Flux 3D Plotter...")
    plotter = MagneticFlux3DPlotter(args.db)

    # Determine time range
    if args.start and args.end:
        start_time = datetime.fromisoformat(args.start)
        end_time = datetime.fromisoformat(args.end)
    elif args.start:
        start_time = datetime.fromisoformat(args.start)
        end_time = datetime.now()
    else:
        if args.days:
            hours = args.days * 24
        else:
            hours = args.hours
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

    print(f"Retrieving data from {start_time} to {end_time}")

    # Get and process data
    raw_data = plotter.get_magnetic_flux_data(start_time, end_time)
    if not raw_data:
        print("No data available for the specified time range.")
        return

    data = plotter.process_data(raw_data)
    if not data:
        print("Failed to process data.")
        return

    # Print statistics
    if not args.no_stats:
        plotter.print_statistics(data)

    # Determine which plots to create
    plot_types = args.plots if 'all' not in args.plots else ['vectors', 'magnitude', 'direction', 'trajectory', 'polar']

    # Create plots
    figures = []

    if 'vectors' in plot_types:
        print("\nCreating 3D vector plot...")
        fig = plotter.create_3d_vector_plot(data)
        figures.append(('magnetic_flux_vectors', fig))

    if 'magnitude' in plot_types:
        print("Creating magnitude vs time plot...")
        fig = plotter.create_magnitude_time_plot(data)
        figures.append(('magnetic_flux_magnitude', fig))

    if 'direction' in plot_types:
        print("Creating direction analysis plot...")
        fig = plotter.create_direction_analysis_plot(data)
        figures.append(('magnetic_flux_direction', fig))

    if 'trajectory' in plot_types:
        print("Creating 3D trajectory plot...")
        fig = plotter.create_3d_trajectory_plot(data)
        figures.append(('magnetic_flux_trajectory', fig))

    if 'polar' in plot_types:
        print("Creating 2D polar plot...")
        fig = plotter.create_2d_polar_plot(data)
        figures.append(('magnetic_flux_polar', fig))

    # Save or display plots
    if args.save:
        # Create output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)

        for filename, fig in figures:
            filepath = os.path.join(args.output_dir, f"{filename}.{args.format}")
            fig.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"Saved: {filepath}")

        print(f"\nAll plots saved to {args.output_dir}/")
    else:
        print("\nDisplaying plots... Close plot windows to exit.")
        plt.show()


if __name__ == "__main__":
    main()