#!/usr/bin/env python3
"""
Virtual Observatory Station Predictor

Main engine for the virtual geomagnetic observatory at Palmer, Alaska.
Combines real-time USGS data collection with ML spatial interpolation
to generate continuous virtual observatory readings.

Features:
- Real-time data collection from 4 nearest USGS observatories
- ML-based spatial interpolation with uncertainty quantification
- Comparison with local sensor measurements for validation
- Time series prediction and forecasting
- Data quality assessment and anomaly detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import argparse
import time

from .observatory_network import ObservatoryNetwork, Observatory
from .spatial_interpolation import SpatialInterpolator, InterpolationResult


class VirtualObservatoryPredictor:
    """Virtual geomagnetic observatory for Palmer, Alaska."""

    def __init__(self, db_path: str = "/deepsink1/weatherstation/data/weather_data.db", config_file: str = None):
        """Initialize virtual observatory predictor."""
        self.db_path = db_path
        self.config = self._load_config(config_file)

        # Initialize network and interpolator
        self.network = ObservatoryNetwork(
            target_lat=self.config['target_location']['latitude'],
            target_lon=self.config['target_location']['longitude']
        )
        self.interpolator = SpatialInterpolator(self.network)

        # Data storage
        self.prediction_history = []
        self.validation_results = []

        print(f"Virtual Observatory initialized for Palmer, Alaska")
        print(f"Target: {self.network.target_lat:.4f}°N, {self.network.target_lon:.4f}°W")

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration or use defaults."""
        default_config = {
            "target_location": {
                "latitude": 61.5994,
                "longitude": -149.115,
                "elevation": 70,
                "name": "Palmer, Alaska"
            },
            "interpolation": {
                "method": "idw",  # 'idw', 'gp', 'ensemble'
                "update_interval_minutes": 5,
                "max_data_age_hours": 2,
                "uncertainty_threshold": 0.1
            },
            "validation": {
                "local_sensor_available": True,
                "validation_interval_hours": 1,
                "alert_threshold_percent": 20
            },
            "data_quality": {
                "min_observatories": 3,
                "max_missing_data_percent": 25,
                "temporal_consistency_check": True
            }
        }

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    for key, value in user_config.items():
                        if isinstance(value, dict) and key in default_config:
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
            except Exception as e:
                print(f"Error loading config: {e}, using defaults")

        return default_config

    def collect_usgs_data(self, time_range_hours: float = 1.0) -> Dict[str, np.ndarray]:
        """
        Collect recent USGS data from the 4 nearest observatories.

        Args:
            time_range_hours: Hours of recent data to collect

        Returns:
            Dictionary mapping observatory codes to [x,y,z] magnetic field arrays (Tesla)
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_range_hours)

        magnetic_data = {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for obs in self.network.get_nearest_observatories():
                # Get most recent data for this observatory
                cursor.execute("""
                    SELECT x, y, z, data_timestamp FROM usgs_magnetic_data
                    WHERE observatory_code = ? AND data_timestamp BETWEEN ? AND ?
                    ORDER BY data_timestamp DESC
                    LIMIT 10
                """, (obs.code, start_time, end_time))

                rows = cursor.fetchall()

                if rows:
                    # Use most recent reading, or average if multiple recent readings
                    if len(rows) == 1:
                        x, y, z, timestamp = rows[0]
                        magnetic_data[obs.code] = np.array([x, y, z])
                    else:
                        # Average recent readings (weighted by recency)
                        x_vals = [row[0] for row in rows]
                        y_vals = [row[1] for row in rows]
                        z_vals = [row[2] for row in rows]

                        # Simple average for now (could add time-weighted average)
                        magnetic_data[obs.code] = np.array([
                            np.mean(x_vals),
                            np.mean(y_vals),
                            np.mean(z_vals)
                        ])

                    print(f"Collected data from {obs.code}: {magnetic_data[obs.code]}")
                else:
                    print(f"Warning: No recent data available from {obs.code}")

            conn.close()

        except Exception as e:
            print(f"Error collecting USGS data: {e}")

        return magnetic_data

    def collect_local_sensor_data(self, time_range_hours: float = 1.0) -> Optional[np.ndarray]:
        """
        Collect recent local sensor data for validation.

        Args:
            time_range_hours: Hours of recent data to collect

        Returns:
            [x,y,z] magnetic field array (Tesla) or None if not available
        """
        if not self.config['validation']['local_sensor_available']:
            return None

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_range_hours)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get most recent local sensor data
            cursor.execute("""
                SELECT x, y, z, created_at FROM magnetic_flux_data
                WHERE created_at BETWEEN ? AND ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (start_time, end_time))

            rows = cursor.fetchall()
            conn.close()

            if rows:
                # Load calibration and apply to raw data
                calibration = self._load_sensor_calibration()

                # Average recent readings
                x_raw = np.mean([row[0] for row in rows])
                y_raw = np.mean([row[1] for row in rows])
                z_raw = np.mean([row[2] for row in rows])

                # Apply calibration (convert LSb to Tesla)
                x_cal = x_raw * calibration['magnetic_flux_x_scale'] + calibration['magnetic_flux_x_offset']
                y_cal = y_raw * calibration['magnetic_flux_y_scale'] + calibration['magnetic_flux_y_offset']
                z_cal = z_raw * calibration['magnetic_flux_z_scale'] + calibration['magnetic_flux_z_offset']

                return np.array([x_cal, y_cal, z_cal])

        except Exception as e:
            print(f"Error collecting local sensor data: {e}")

        return None

    def _load_sensor_calibration(self) -> Dict:
        """Load local sensor calibration values."""
        default_calibration = {
            'magnetic_flux_x_scale': 5.119362344461532e-08,
            'magnetic_flux_y_scale': 5.468460042213421e-09,
            'magnetic_flux_z_scale': 3.285602009007802e-08,
            'magnetic_flux_x_offset': 5.254899604336113e-09,
            'magnetic_flux_y_offset': -4.11262082740767e-09,
            'magnetic_flux_z_offset': -9.87942500592625e-09
        }

        try:
            with open("../weather_station_calibration.json", 'r') as f:
                data = json.load(f)
                return data.get('calibration', default_calibration)
        except:
            return default_calibration

    def generate_virtual_reading(self) -> InterpolationResult:
        """
        Generate a virtual observatory reading using ML interpolation.

        Returns:
            InterpolationResult with virtual magnetic field measurement
        """
        # Collect USGS data
        usgs_data = self.collect_usgs_data(
            self.config['interpolation']['max_data_age_hours']
        )

        if len(usgs_data) < self.config['data_quality']['min_observatories']:
            raise RuntimeError(f"Insufficient USGS data: only {len(usgs_data)} observatories available")

        # Perform interpolation
        method = self.config['interpolation']['method']
        result = self.interpolator.interpolate_magnetic_field(usgs_data, method)

        # Add quality assessment
        quality_score = self.interpolator.get_interpolation_quality_score(result)
        result.quality_score = quality_score

        # Store in history
        self.prediction_history.append({
            'timestamp': result.timestamp,
            'result': result,
            'usgs_data': usgs_data,
            'quality_score': quality_score
        })

        # Keep only recent history
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.prediction_history = [
            p for p in self.prediction_history
            if p['timestamp'] > cutoff_time
        ]

        return result

    def validate_against_local_sensor(self, virtual_result: InterpolationResult) -> Dict:
        """
        Validate virtual observatory reading against local sensor.

        Args:
            virtual_result: Virtual observatory prediction

        Returns:
            Dictionary with validation metrics
        """
        local_data = self.collect_local_sensor_data(0.5)  # 30 minutes

        if local_data is None:
            return {"status": "no_local_data"}

        # Calculate differences
        diff_x = virtual_result.x_component - local_data[0]
        diff_y = virtual_result.y_component - local_data[1]
        diff_z = virtual_result.z_component - local_data[2]

        virtual_mag = virtual_result.magnitude
        local_mag = np.sqrt(np.sum(local_data**2))
        diff_magnitude = virtual_mag - local_mag

        # Calculate percentage differences
        percent_diff_mag = abs(diff_magnitude / local_mag) * 100

        validation = {
            "status": "validated",
            "timestamp": datetime.now(),
            "local_magnitude": local_mag,
            "virtual_magnitude": virtual_mag,
            "difference_magnitude": diff_magnitude,
            "percent_difference": percent_diff_mag,
            "differences": {
                "x": diff_x,
                "y": diff_y,
                "z": diff_z
            },
            "within_threshold": percent_diff_mag < self.config['validation']['alert_threshold_percent']
        }

        self.validation_results.append(validation)

        # Alert if large discrepancy
        if not validation["within_threshold"]:
            print(f"⚠️  VALIDATION ALERT: {percent_diff_mag:.1f}% difference exceeds threshold")

        return validation

    def run_continuous_prediction(self, duration_hours: float = 1.0, update_interval_minutes: float = 5.0):
        """
        Run continuous virtual observatory predictions.

        Args:
            duration_hours: How long to run predictions
            update_interval_minutes: How often to update predictions
        """
        print(f"\nStarting continuous virtual observatory predictions...")
        print(f"Duration: {duration_hours} hours, Update interval: {update_interval_minutes} minutes")
        print("="*70)

        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)

        prediction_count = 0

        while datetime.now() < end_time:
            try:
                # Generate virtual reading
                virtual_result = self.generate_virtual_reading()
                prediction_count += 1

                print(f"\n[{virtual_result.timestamp.strftime('%H:%M:%S')}] Virtual Observatory Reading #{prediction_count}")
                print(f"Magnetic Field: {virtual_result.magnitude*1e9:.1f} ± {virtual_result.uncertainty_mag*1e9:.1f} nT")
                print(f"Components: X={virtual_result.x_component*1e9:.1f}, Y={virtual_result.y_component*1e9:.1f}, Z={virtual_result.z_component*1e9:.1f} nT")
                print(f"Method: {virtual_result.method}, Quality: {getattr(virtual_result, 'quality_score', 0):.3f}")

                # Validate against local sensor
                if self.config['validation']['local_sensor_available']:
                    validation = self.validate_against_local_sensor(virtual_result)
                    if validation['status'] == 'validated':
                        print(f"Local Validation: {validation['percent_difference']:.1f}% difference ({'✓' if validation['within_threshold'] else '⚠️'})")

                # Wait for next update
                time.sleep(update_interval_minutes * 60)

            except KeyboardInterrupt:
                print("\nStopping continuous predictions...")
                break
            except Exception as e:
                print(f"Error in prediction: {e}")
                time.sleep(30)  # Wait 30 seconds before retrying

        print(f"\nCompleted {prediction_count} virtual observatory predictions")

    def get_prediction_summary(self) -> Dict:
        """Get summary of recent predictions and validation."""
        if not self.prediction_history:
            return {"status": "no_data"}

        recent_predictions = self.prediction_history[-10:]  # Last 10 predictions

        magnitudes = [p['result'].magnitude * 1e9 for p in recent_predictions]
        uncertainties = [p['result'].uncertainty_mag * 1e9 for p in recent_predictions]
        quality_scores = [p.get('quality_score', 0) for p in recent_predictions]

        summary = {
            "status": "active",
            "num_predictions": len(self.prediction_history),
            "recent_predictions": len(recent_predictions),
            "magnitude_stats": {
                "mean": np.mean(magnitudes),
                "std": np.std(magnitudes),
                "min": np.min(magnitudes),
                "max": np.max(magnitudes)
            },
            "uncertainty_stats": {
                "mean": np.mean(uncertainties),
                "std": np.std(uncertainties)
            },
            "quality_stats": {
                "mean": np.mean(quality_scores),
                "min": np.min(quality_scores),
                "max": np.max(quality_scores)
            }
        }

        # Validation summary
        if self.validation_results:
            recent_validations = self.validation_results[-10:]
            percent_diffs = [v['percent_difference'] for v in recent_validations if 'percent_difference' in v]

            if percent_diffs:
                summary["validation_stats"] = {
                    "mean_difference_percent": np.mean(percent_diffs),
                    "max_difference_percent": np.max(percent_diffs),
                    "within_threshold_count": sum(1 for v in recent_validations if v.get('within_threshold', False)),
                    "total_validations": len(recent_validations)
                }

        return summary

    def save_prediction_data(self, filename: str):
        """Save prediction history to file."""
        data = {
            "virtual_observatory": {
                "location": {
                    "latitude": self.network.target_lat,
                    "longitude": self.network.target_lon,
                    "name": self.config['target_location']['name']
                },
                "observatories_used": [
                    {
                        "code": obs.code,
                        "name": obs.name,
                        "distance_km": obs.distance_km
                    }
                    for obs in self.network.get_nearest_observatories()
                ]
            },
            "predictions": [
                {
                    "timestamp": p['timestamp'].isoformat(),
                    "magnitude_nt": p['result'].magnitude * 1e9,
                    "uncertainty_nt": p['result'].uncertainty_mag * 1e9,
                    "components_nt": {
                        "x": p['result'].x_component * 1e9,
                        "y": p['result'].y_component * 1e9,
                        "z": p['result'].z_component * 1e9
                    },
                    "method": p['result'].method,
                    "quality_score": p.get('quality_score', 0)
                }
                for p in self.prediction_history
            ],
            "validations": self.validation_results,
            "created": datetime.now().isoformat()
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        print(f"Saved prediction data to {filename}")


def main():
    """Main function for virtual observatory."""
    parser = argparse.ArgumentParser(description='Virtual Geomagnetic Observatory for Palmer, Alaska')
    parser.add_argument('--mode', choices=['single', 'continuous'], default='single',
                        help='Prediction mode')
    parser.add_argument('--duration', type=float, default=1.0,
                        help='Duration for continuous mode (hours)')
    parser.add_argument('--interval', type=float, default=5.0,
                        help='Update interval for continuous mode (minutes)')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--save', help='Save predictions to file')
    parser.add_argument('--db', default='/deepsink1/weatherstation/data/weather_data.db', help='Database path')

    args = parser.parse_args()

    print("Palmer, Alaska Virtual Geomagnetic Observatory")
    print("="*50)

    # Initialize virtual observatory
    virtual_obs = VirtualObservatoryPredictor(args.db, args.config)

    # Print network summary
    virtual_obs.network.print_network_summary()

    if args.mode == 'single':
        # Single prediction
        try:
            result = virtual_obs.generate_virtual_reading()

            print(f"\n🌐 VIRTUAL OBSERVATORY READING")
            print(f"Timestamp: {result.timestamp}")
            print(f"Location: Palmer, Alaska ({virtual_obs.network.target_lat:.4f}°N, {virtual_obs.network.target_lon:.4f}°W)")
            print(f"Method: {result.method}")
            print(f"")
            print(f"Magnetic Field Components:")
            print(f"  X (North): {result.x_component*1e9:8.1f} ± {result.uncertainty_x*1e9:5.1f} nT")
            print(f"  Y (East):  {result.y_component*1e9:8.1f} ± {result.uncertainty_y*1e9:5.1f} nT")
            print(f"  Z (Down):  {result.z_component*1e9:8.1f} ± {result.uncertainty_z*1e9:5.1f} nT")
            print(f"")
            print(f"Total Field: {result.magnitude*1e9:8.1f} ± {result.uncertainty_mag*1e9:5.1f} nT")
            print(f"Quality Score: {getattr(result, 'quality_score', 0):.3f}")

            # Validate against local sensor
            validation = virtual_obs.validate_against_local_sensor(result)
            if validation['status'] == 'validated':
                print(f"\n📊 LOCAL SENSOR VALIDATION")
                print(f"Local Magnitude: {validation['local_magnitude']*1e9:.1f} nT")
                print(f"Difference: {validation['difference_magnitude']*1e9:+.1f} nT ({validation['percent_difference']:+.1f}%)")
                print(f"Within Threshold: {'✓ Yes' if validation['within_threshold'] else '⚠️  No'}")

        except Exception as e:
            print(f"Error generating prediction: {e}")

    elif args.mode == 'continuous':
        # Continuous predictions
        virtual_obs.run_continuous_prediction(args.duration, args.interval)

        # Print summary
        summary = virtual_obs.get_prediction_summary()
        if summary['status'] == 'active':
            print(f"\n📈 PREDICTION SUMMARY")
            print(f"Total Predictions: {summary['num_predictions']}")
            print(f"Average Magnitude: {summary['magnitude_stats']['mean']:.1f} ± {summary['magnitude_stats']['std']:.1f} nT")
            print(f"Average Quality: {summary['quality_stats']['mean']:.3f}")

            if 'validation_stats' in summary:
                vs = summary['validation_stats']
                print(f"Average Validation Difference: {vs['mean_difference_percent']:.1f}%")
                print(f"Validation Success Rate: {vs['within_threshold_count']}/{vs['total_validations']}")

    # Save data if requested
    if args.save:
        virtual_obs.save_prediction_data(args.save)


if __name__ == "__main__":
    main()