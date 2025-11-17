#!/usr/bin/env python3
"""
Magnetic Coordinate Calibrator

This utility performs coordinate transformations and calibration optimization
to align local HMC5883L sensor data with USGS reference data, accounting for
sensor orientation, scale factors, and offset corrections.

Features:
- 3D rotation matrix optimization
- Scale factor calibration
- Offset correction
- Statistical analysis of transformation quality
- Visualization of before/after alignment

Usage:
    python magnetic_coordinate_calibrator.py --observatory CMO --hours 8
    python magnetic_coordinate_calibrator.py --observatory CMO --hours 12 --save-calibration
"""

import argparse
import sqlite3
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from datetime import datetime, timedelta
import json
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R
import os

class MagneticCoordinateCalibrator:
    """Calibrates sensor orientation and scale using USGS reference data."""

    def __init__(self, db_path="/deepsink1/weatherstation/data/weather_data.db"):
        self.db_path = db_path
        self.best_transformation = None
        self.calibration_results = None

    def load_aligned_data(self, observatory_code, hours=8):
        """Load and align local and USGS data for calibration."""
        print(f"Loading data for calibration analysis...")

        # Time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # Load both datasets
        local_data = self.load_local_data(start_time, end_time)
        usgs_data = self.load_usgs_data(observatory_code, start_time, end_time)

        if not local_data or not usgs_data:
            print("Error: Could not load required data")
            return None, None

        # Align time series
        aligned_local, aligned_usgs = self.align_time_series(local_data, usgs_data)

        if not aligned_local or not aligned_usgs:
            print("Error: Could not align time series")
            return None, None

        print(f"Loaded {len(aligned_local['x'])} aligned data points for calibration")
        return aligned_local, aligned_usgs

    def load_local_data(self, start_time, end_time):
        """Load local sensor data (raw LSb values)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT x, y, z, created_at
                FROM magnetic_flux_data
                WHERE created_at BETWEEN ? AND ?
                ORDER BY created_at ASC
            """, (start_time, end_time))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return None

            times = []
            x_values = []
            y_values = []
            z_values = []

            for row in rows:
                x, y, z, timestamp_str = row
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', ''))
                times.append(timestamp)
                # Store raw LSb values for calibration
                x_values.append(float(x))
                y_values.append(float(y))
                z_values.append(float(z))

            return {
                'times': np.array(times),
                'x': np.array(x_values),
                'y': np.array(y_values),
                'z': np.array(z_values)
            }

        except Exception as e:
            print(f"Error loading local data: {e}")
            return None

    def load_usgs_data(self, observatory_code, start_time, end_time):
        """Load USGS reference data (Tesla values)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT x, y, z, data_timestamp
                FROM usgs_magnetic_data
                WHERE observatory_code = ? AND data_timestamp BETWEEN ? AND ?
                ORDER BY data_timestamp ASC
            """, (observatory_code, start_time, end_time))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return None

            times = []
            x_values = []
            y_values = []
            z_values = []

            for row in rows:
                x, y, z, timestamp_str = row
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', ''))
                times.append(timestamp)
                # Convert Tesla to nanotesla for easier comparison
                x_values.append(float(x) * 1e9)
                y_values.append(float(y) * 1e9)
                z_values.append(float(z) * 1e9)

            return {
                'times': np.array(times),
                'x': np.array(x_values),
                'y': np.array(y_values),
                'z': np.array(z_values)
            }

        except Exception as e:
            print(f"Error loading USGS data: {e}")
            return None

    def align_time_series(self, local_data, usgs_data, tolerance_minutes=5):
        """Align local and USGS data by timestamp."""
        tolerance = timedelta(minutes=tolerance_minutes)

        aligned_local = {'x': [], 'y': [], 'z': []}
        aligned_usgs = {'x': [], 'y': [], 'z': []}

        # Convert timestamps to naive for comparison
        local_times = [t.replace(tzinfo=None) if hasattr(t, 'tzinfo') and t.tzinfo else t
                      for t in local_data['times']]
        usgs_times = [t.replace(tzinfo=None) if hasattr(t, 'tzinfo') and t.tzinfo else t
                     for t in usgs_data['times']]

        usgs_times = np.array(usgs_times)

        for i, local_time in enumerate(local_times):
            time_diffs = np.abs(usgs_times - local_time)
            min_diff_idx = np.argmin(time_diffs)

            if time_diffs[min_diff_idx] <= tolerance:
                aligned_local['x'].append(local_data['x'][i])
                aligned_local['y'].append(local_data['y'][i])
                aligned_local['z'].append(local_data['z'][i])

                aligned_usgs['x'].append(usgs_data['x'][min_diff_idx])
                aligned_usgs['y'].append(usgs_data['y'][min_diff_idx])
                aligned_usgs['z'].append(usgs_data['z'][min_diff_idx])

        # Convert to numpy arrays
        for key in ['x', 'y', 'z']:
            aligned_local[key] = np.array(aligned_local[key])
            aligned_usgs[key] = np.array(aligned_usgs[key])

        return aligned_local, aligned_usgs

    def transformation_objective(self, params, local_data, usgs_data):
        """Objective function for transformation optimization."""
        # Extract parameters
        # params = [scale_x, scale_y, scale_z, rot_x, rot_y, rot_z, offset_x, offset_y, offset_z]
        scale_factors = params[0:3]
        rotation_angles = params[3:6]  # Euler angles in radians
        offsets = params[6:9]

        # Apply scale factors to local data (convert LSb to nT)
        local_scaled = np.column_stack([
            local_data['x'] * scale_factors[0],
            local_data['y'] * scale_factors[1],
            local_data['z'] * scale_factors[2]
        ])

        # Apply rotation
        rotation = R.from_euler('xyz', rotation_angles)
        local_rotated = rotation.apply(local_scaled)

        # Apply offsets
        local_transformed = local_rotated + offsets

        # Calculate RMS error against USGS reference
        usgs_vectors = np.column_stack([usgs_data['x'], usgs_data['y'], usgs_data['z']])

        errors = local_transformed - usgs_vectors
        rms_error = np.sqrt(np.mean(np.sum(errors**2, axis=1)))

        return rms_error

    def optimize_transformation(self, local_data, usgs_data):
        """Find optimal transformation parameters."""
        print("Optimizing coordinate transformation...")

        # Initial parameter estimates
        # Rough scale factor estimate (convert LSb to nT)
        usgs_mag = np.sqrt(usgs_data['x']**2 + usgs_data['y']**2 + usgs_data['z']**2)
        local_mag = np.sqrt(local_data['x']**2 + local_data['y']**2 + local_data['z']**2)

        initial_scale = np.mean(usgs_mag) / np.mean(local_mag)

        # Initial parameters: [scale_x, scale_y, scale_z, rot_x, rot_y, rot_z, offset_x, offset_y, offset_z]
        initial_params = [
            initial_scale, initial_scale, initial_scale,  # Scale factors
            0.0, 0.0, 0.0,                               # Rotation angles (radians)
            0.0, 0.0, 0.0                                # Offsets (nT)
        ]

        print(f"Initial scale estimate: {initial_scale:.2e}")

        # Parameter bounds
        bounds = [
            (initial_scale*0.1, initial_scale*10),  # scale_x
            (initial_scale*0.1, initial_scale*10),  # scale_y
            (initial_scale*0.1, initial_scale*10),  # scale_z
            (-np.pi, np.pi),                        # rot_x
            (-np.pi, np.pi),                        # rot_y
            (-np.pi, np.pi),                        # rot_z
            (-50000, 50000),                        # offset_x (nT)
            (-50000, 50000),                        # offset_y (nT)
            (-50000, 50000)                         # offset_z (nT)
        ]

        # Optimize
        result = minimize(
            self.transformation_objective,
            initial_params,
            args=(local_data, usgs_data),
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': 1000, 'disp': True}
        )

        if result.success:
            print(f"Optimization successful! RMS error: {result.fun:.2f} nT")
            self.best_transformation = {
                'scale_factors': result.x[0:3],
                'rotation_angles': result.x[3:6],
                'offsets': result.x[6:9],
                'rms_error': result.fun
            }
            return self.best_transformation
        else:
            print(f"Optimization failed: {result.message}")
            return None

    def apply_transformation(self, local_data, transformation):
        """Apply the optimized transformation to local data."""
        # Apply scale factors
        local_scaled = np.column_stack([
            local_data['x'] * transformation['scale_factors'][0],
            local_data['y'] * transformation['scale_factors'][1],
            local_data['z'] * transformation['scale_factors'][2]
        ])

        # Apply rotation
        rotation = R.from_euler('xyz', transformation['rotation_angles'])
        local_rotated = rotation.apply(local_scaled)

        # Apply offsets
        local_transformed = local_rotated + transformation['offsets']

        return {
            'x': local_transformed[:, 0],
            'y': local_transformed[:, 1],
            'z': local_transformed[:, 2]
        }

    def analyze_results(self, local_original, local_transformed, usgs_data, transformation):
        """Analyze transformation results and print statistics."""
        print("\n" + "="*80)
        print("COORDINATE TRANSFORMATION ANALYSIS")
        print("="*80)

        # Print transformation parameters
        print(f"\nOptimal Transformation Parameters:")
        print(f"Scale Factors (LSb to nT):")
        print(f"  X: {transformation['scale_factors'][0]:.6e}")
        print(f"  Y: {transformation['scale_factors'][1]:.6e}")
        print(f"  Z: {transformation['scale_factors'][2]:.6e}")

        print(f"\nRotation Angles (degrees):")
        angles_deg = np.degrees(transformation['rotation_angles'])
        print(f"  X-axis: {angles_deg[0]:.2f}°")
        print(f"  Y-axis: {angles_deg[1]:.2f}°")
        print(f"  Z-axis: {angles_deg[2]:.2f}°")

        print(f"\nOffsets (nT):")
        print(f"  X: {transformation['offsets'][0]:.2f}")
        print(f"  Y: {transformation['offsets'][1]:.2f}")
        print(f"  Z: {transformation['offsets'][2]:.2f}")

        # Calculate statistics
        components = ['x', 'y', 'z']

        print(f"\nBEFORE vs AFTER TRANSFORMATION:")
        print("-" * 60)

        for i, comp in enumerate(components):
            # Original comparison (scaled by initial calibration)
            original_scaled = local_original[comp] * 9.174e-8 * 1e9  # Convert to nT
            usgs_vals = usgs_data[comp]
            transformed_vals = local_transformed[comp]

            # Statistics
            orig_rms = np.sqrt(np.mean((original_scaled - usgs_vals)**2))
            trans_rms = np.sqrt(np.mean((transformed_vals - usgs_vals)**2))

            orig_corr = np.corrcoef(original_scaled, usgs_vals)[0, 1]
            trans_corr = np.corrcoef(transformed_vals, usgs_vals)[0, 1]

            improvement = ((orig_rms - trans_rms) / orig_rms) * 100

            print(f"\n{comp.upper()} Component:")
            print(f"  USGS Mean:           {np.mean(usgs_vals):8.2f} nT")
            print(f"  Original RMS Error:  {orig_rms:8.2f} nT (r={orig_corr:.3f})")
            print(f"  Transformed RMS:     {trans_rms:8.2f} nT (r={trans_corr:.3f})")
            print(f"  Improvement:         {improvement:8.1f}%")

        # Overall magnitude comparison
        usgs_mag = np.sqrt(usgs_data['x']**2 + usgs_data['y']**2 + usgs_data['z']**2)
        trans_mag = np.sqrt(local_transformed['x']**2 + local_transformed['y']**2 + local_transformed['z']**2)

        mag_rms = np.sqrt(np.mean((trans_mag - usgs_mag)**2))
        mag_corr = np.corrcoef(trans_mag, usgs_mag)[0, 1]

        print(f"\nMAGNITUDE:")
        print(f"  USGS Mean:           {np.mean(usgs_mag):8.2f} nT")
        print(f"  Transformed Mean:    {np.mean(trans_mag):8.2f} nT")
        print(f"  RMS Error:           {mag_rms:8.2f} nT")
        print(f"  Correlation:         {mag_corr:8.3f}")

        print(f"\nOverall RMS Error: {transformation['rms_error']:.2f} nT")
        print("="*80)

    def create_calibration_plots(self, local_original, local_transformed, usgs_data, save=False):
        """Create before/after comparison plots."""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('Coordinate Transformation Results', fontsize=16, fontweight='bold')

        components = ['x', 'y', 'z']
        component_names = ['X (North)', 'Y (East)', 'Z (Down)']

        # Before transformation (top row)
        for i, (comp, name) in enumerate(zip(components, component_names)):
            ax = axes[0, i]

            # Convert original to nT using initial calibration
            original_nt = local_original[comp] * 9.174e-8 * 1e9
            usgs_vals = usgs_data[comp]

            ax.scatter(usgs_vals, original_nt, alpha=0.6, s=10, c='red', label='Original')

            # Perfect correlation line
            min_val = min(np.min(original_nt), np.min(usgs_vals))
            max_val = max(np.max(original_nt), np.max(usgs_vals))
            ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='Perfect correlation')

            ax.set_xlabel(f'USGS {name} (nT)')
            ax.set_ylabel(f'Local {name} (nT)')
            ax.set_title(f'BEFORE: {name}')
            ax.grid(True, alpha=0.3)
            ax.legend()

        # After transformation (bottom row)
        for i, (comp, name) in enumerate(zip(components, component_names)):
            ax = axes[1, i]

            transformed_vals = local_transformed[comp]
            usgs_vals = usgs_data[comp]

            ax.scatter(usgs_vals, transformed_vals, alpha=0.6, s=10, c='blue', label='Transformed')

            # Perfect correlation line
            min_val = min(np.min(transformed_vals), np.min(usgs_vals))
            max_val = max(np.max(transformed_vals), np.max(usgs_vals))
            ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='Perfect correlation')

            # Calculate and display correlation
            corr = np.corrcoef(transformed_vals, usgs_vals)[0, 1]
            ax.text(0.05, 0.95, f'r = {corr:.3f}', transform=ax.transAxes,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

            ax.set_xlabel(f'USGS {name} (nT)')
            ax.set_ylabel(f'Local {name} (nT)')
            ax.set_title(f'AFTER: {name}')
            ax.grid(True, alpha=0.3)
            ax.legend()

        plt.tight_layout()

        if save:
            os.makedirs('calibration_plots', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'calibration_plots/coordinate_transformation_{timestamp}.png'
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            print(f"Saved calibration plot: {filename}")
        else:
            plt.show()

    def save_calibration_config(self, transformation, observatory_code):
        """Save the optimized calibration to configuration file."""
        calibration_data = {
            "version": "2.0",
            "created": datetime.now().isoformat(),
            "description": f"Coordinate transformation calibration using {observatory_code} reference",
            "reference_observatory": observatory_code,
            "calibration_values": {
                "magnetic_flux_x_scale": float(transformation['scale_factors'][0] * 1e-9),  # Convert to T/LSb
                "magnetic_flux_y_scale": float(transformation['scale_factors'][1] * 1e-9),
                "magnetic_flux_z_scale": float(transformation['scale_factors'][2] * 1e-9),
                "magnetic_flux_x_offset": float(transformation['offsets'][0] * 1e-9),       # Convert to T
                "magnetic_flux_y_offset": float(transformation['offsets'][1] * 1e-9),
                "magnetic_flux_z_offset": float(transformation['offsets'][2] * 1e-9)
            },
            "coordinate_transformation": {
                "rotation_x_degrees": float(np.degrees(transformation['rotation_angles'][0])),
                "rotation_y_degrees": float(np.degrees(transformation['rotation_angles'][1])),
                "rotation_z_degrees": float(np.degrees(transformation['rotation_angles'][2])),
                "rms_error_nt": float(transformation['rms_error'])
            }
        }

        filename = "weather_station_calibration_optimized.json"
        with open(filename, 'w') as f:
            json.dump(calibration_data, f, indent=2)

        print(f"\nOptimized calibration saved to: {filename}")
        print("To use this calibration, update your weather_station_calibration.json with these values.")

def main():
    parser = argparse.ArgumentParser(description='Optimize sensor coordinate transformation using USGS reference data')
    parser.add_argument('--observatory', '-o', default='CMO', help='USGS observatory code for reference')
    parser.add_argument('--hours', type=int, default=8, help='Hours of data to use for calibration')
    parser.add_argument('--db', default='/deepsink1/weatherstation/data/weather_data.db', help='Database path')
    parser.add_argument('--save-plots', action='store_true', help='Save calibration plots')
    parser.add_argument('--save-calibration', action='store_true', help='Save optimized calibration to file')

    args = parser.parse_args()

    print(f"Magnetic Coordinate Calibrator")
    print(f"Observatory: {args.observatory}")
    print(f"Data range: {args.hours} hours")
    print("="*50)

    # Create calibrator
    calibrator = MagneticCoordinateCalibrator(args.db)

    # Load aligned data
    local_data, usgs_data = calibrator.load_aligned_data(args.observatory, args.hours)

    if local_data is None or usgs_data is None:
        print("Error: Could not load calibration data")
        return

    # Optimize transformation
    transformation = calibrator.optimize_transformation(local_data, usgs_data)

    if transformation is None:
        print("Error: Optimization failed")
        return

    # Apply transformation
    local_transformed = calibrator.apply_transformation(local_data, transformation)

    # Analyze results
    calibrator.analyze_results(local_data, local_transformed, usgs_data, transformation)

    # Create plots
    calibrator.create_calibration_plots(local_data, local_transformed, usgs_data, save=args.save_plots)

    # Save calibration if requested
    if args.save_calibration:
        calibrator.save_calibration_config(transformation, args.observatory)

if __name__ == "__main__":
    main()