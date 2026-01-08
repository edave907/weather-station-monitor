#!/usr/bin/env python3
"""
Virtual Observatory Setup Script
Automated creation of synthetic geomagnetic observatories

This script helps users create virtual observatories for any location worldwide
by automatically configuring the network, generating configurations, and
testing the interpolation system.

Usage:
    ./venv/bin/python create_virtual_observatory.py --location "City, State/Country" --lat 64.8378 --lon -147.7164
    ./venv/bin/python create_virtual_observatory.py --interactive
"""

import argparse
import json
import os
import numpy as np
from datetime import datetime
from typing import Dict, Tuple, Optional

from virtual_observatory.observatory_network import ObservatoryNetwork
from virtual_observatory.spatial_interpolation import SpatialInterpolator
from virtual_observatory.virtual_station_predictor import VirtualObservatoryPredictor


class VirtualObservatorySetup:
    """Setup and configuration tool for virtual observatories."""

    def __init__(self):
        """Initialize the setup tool."""
        self.config_dir = "config"
        self.ensure_config_directory()

        # Common magnetic declination values (approximate)
        self.declination_lookup = {
            # Alaska
            "anchorage": -17.0, "fairbanks": -15.8, "juneau": -18.5, "nome": -14.2,
            "barrow": -12.5, "palmer": -17.5,
            # Continental US
            "seattle": 16.2, "portland": 15.8, "san_francisco": 13.8, "los_angeles": 12.1,
            "denver": 8.5, "chicago": -3.2, "new_york": -13.6, "miami": -5.1,
            # International (approximate)
            "reykjavik": -11.5, "tromso": 2.5, "stockholm": 5.2, "oslo": 1.8,
            "london": 0.2, "paris": 1.2, "berlin": 2.8, "moscow": 10.5,
            "tokyo": -7.1, "sydney": 12.5, "auckland": 20.2
        }

    def ensure_config_directory(self):
        """Ensure config directory exists."""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def get_magnetic_declination(self, location_name: str, latitude: float) -> float:
        """
        Estimate magnetic declination for a location.

        Args:
            location_name: Name of the location
            latitude: Latitude in degrees

        Returns:
            Estimated magnetic declination in degrees
        """
        # Check lookup table first
        location_key = location_name.lower().replace(" ", "").replace(",", "")
        if location_key in self.declination_lookup:
            return self.declination_lookup[location_key]

        # Rough approximation based on latitude (very crude)
        if latitude > 60:  # High northern latitudes
            return -15.0 + (latitude - 60) * 0.5
        elif latitude > 30:  # Mid latitudes
            return -5.0 + (latitude - 30) * 0.3
        elif latitude > 0:  # Low northern latitudes
            return 0.0 + latitude * 0.2
        else:  # Southern hemisphere
            return 10.0 + abs(latitude) * 0.3

    def create_configuration(self, location_name: str, latitude: float,
                           longitude: float, elevation: float = 0) -> Dict:
        """
        Create configuration for a new virtual observatory.

        Args:
            location_name: Human-readable location name
            latitude: Target latitude in decimal degrees
            longitude: Target longitude in decimal degrees
            elevation: Elevation in meters above sea level

        Returns:
            Configuration dictionary
        """
        declination = self.get_magnetic_declination(location_name, latitude)

        config = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "description": f"Virtual Geomagnetic Observatory Configuration for {location_name}",

            "target_location": {
                "latitude": latitude,
                "longitude": longitude,
                "elevation": elevation,
                "name": location_name,
                "magnetic_declination": declination,
                "comments": f"Auto-generated configuration for {location_name}"
            },

            "interpolation": {
                "method": "idw",
                "update_interval_minutes": 5,
                "max_data_age_hours": 2,
                "uncertainty_threshold": 0.1,
                "idw_power": 2.0,
                "gp_kernel_length_scale": 100.0,
                "ensemble_weights": {
                    "idw": 0.3,
                    "gp": 0.7
                }
            },

            "validation": {
                "local_sensor_available": False,
                "validation_interval_hours": 1,
                "alert_threshold_percent": 20,
                "validation_window_minutes": 30,
                "enable_alerts": True
            },

            "data_quality": {
                "min_observatories": 3,
                "max_missing_data_percent": 25,
                "temporal_consistency_check": True,
                "outlier_detection": True,
                "outlier_threshold_sigma": 3.0
            },

            "observatory_network": {
                "preferred_observatories": [],  # Will be auto-determined
                "fallback_observatories": ["BOU", "FRD", "TUC", "NEW"],
                "max_distance_km": 2000,
                "weight_by_distance": True
            },

            "prediction_storage": {
                "keep_history_hours": 24,
                "auto_save_interval_hours": 6,
                "save_format": "json",
                "compress_old_data": True
            },

            "alerts": {
                "large_field_change_threshold_nt": 1000,
                "rapid_change_threshold_nt_per_minute": 50,
                "validation_failure_threshold": 3,
                "data_outage_threshold_minutes": 30
            },

            "performance": {
                "enable_caching": True,
                "cache_duration_minutes": 10,
                "parallel_processing": False,
                "max_memory_mb": 100
            },

            "logging": {
                "level": "INFO",
                "log_predictions": True,
                "log_validations": True,
                "log_file": f"virtual_observatory_{location_name.lower().replace(' ', '_').replace(',', '')}.log",
                "rotate_logs": True
            }
        }

        return config

    def analyze_network(self, latitude: float, longitude: float) -> Tuple[ObservatoryNetwork, Dict]:
        """
        Analyze the observatory network for a given location.

        Args:
            latitude: Target latitude
            longitude: Target longitude

        Returns:
            Tuple of (network, geometry_analysis)
        """
        network = ObservatoryNetwork(target_lat=latitude, target_lon=longitude)
        geometry = network.validate_network_geometry()

        return network, geometry

    def test_interpolation(self, network: ObservatoryNetwork,
                         location_name: str) -> Dict:
        """
        Test interpolation methods for the network.

        Args:
            network: Observatory network
            location_name: Location name for context

        Returns:
            Test results dictionary
        """
        interpolator = SpatialInterpolator(network)

        # Generate realistic test data based on network observatories
        test_data = {}
        for obs in network.nearest_four:
            # Use approximate magnetic field values based on observatory location
            if obs.latitude > 65:  # High latitude
                base_field = np.array([57e-6, 1.5e-6, 55e-6])
            elif obs.latitude > 50:  # Mid latitude
                base_field = np.array([55e-6, 2.0e-6, 53e-6])
            else:  # Lower latitude
                base_field = np.array([52e-6, 2.5e-6, 50e-6])

            # Add small random variation
            variation = np.random.normal(0, 0.001, 3)
            test_data[obs.code] = base_field + variation

        # Test all interpolation methods
        results = {}

        try:
            # IDW method
            result_idw = interpolator.inverse_distance_weighting(test_data)
            quality_idw = interpolator.get_interpolation_quality_score(result_idw)
            results['IDW'] = {
                'magnitude': result_idw.magnitude * 1e6,
                'components': [result_idw.x_component * 1e6,
                             result_idw.y_component * 1e6,
                             result_idw.z_component * 1e6],
                'uncertainty': result_idw.uncertainty_mag * 1e6,
                'quality': quality_idw,
                'success': True
            }
        except Exception as e:
            results['IDW'] = {'success': False, 'error': str(e)}

        try:
            # Gaussian Process method
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                result_gp = interpolator.gaussian_process_interpolation(test_data)
                quality_gp = interpolator.get_interpolation_quality_score(result_gp)
                results['GP'] = {
                    'magnitude': result_gp.magnitude * 1e6,
                    'components': [result_gp.x_component * 1e6,
                                 result_gp.y_component * 1e6,
                                 result_gp.z_component * 1e6],
                    'uncertainty': result_gp.uncertainty_mag * 1e6,
                    'quality': quality_gp,
                    'success': True
                }
        except Exception as e:
            results['GP'] = {'success': False, 'error': str(e)}

        try:
            # Ensemble method
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                result_ensemble = interpolator.ensemble_interpolation(test_data)
                quality_ensemble = interpolator.get_interpolation_quality_score(result_ensemble)
                results['Ensemble'] = {
                    'magnitude': result_ensemble.magnitude * 1e6,
                    'components': [result_ensemble.x_component * 1e6,
                                 result_ensemble.y_component * 1e6,
                                 result_ensemble.z_component * 1e6],
                    'uncertainty': result_ensemble.uncertainty_mag * 1e6,
                    'quality': quality_ensemble,
                    'success': True
                }
        except Exception as e:
            results['Ensemble'] = {'success': False, 'error': str(e)}

        return results

    def save_configuration(self, config: Dict, location_name: str) -> str:
        """
        Save configuration to file.

        Args:
            config: Configuration dictionary
            location_name: Location name for filename

        Returns:
            Path to saved configuration file
        """
        # Generate filename
        safe_name = location_name.lower().replace(" ", "_").replace(",", "").replace(".", "")
        filename = f"virtual_observatory_{safe_name}_config.json"
        filepath = os.path.join(self.config_dir, filename)

        # Update preferred observatories in config
        temp_network = ObservatoryNetwork(
            target_lat=config['target_location']['latitude'],
            target_lon=config['target_location']['longitude']
        )
        config['observatory_network']['preferred_observatories'] = [
            obs.code for obs in temp_network.nearest_four
        ]

        # Save to file
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)

        return filepath

    def create_virtual_observatory(self, location_name: str, latitude: float,
                                 longitude: float, elevation: float = 0,
                                 interactive: bool = False) -> str:
        """
        Complete virtual observatory creation process.

        Args:
            location_name: Human-readable location name
            latitude: Target latitude in decimal degrees
            longitude: Target longitude in decimal degrees
            elevation: Elevation in meters
            interactive: Whether to prompt for user input

        Returns:
            Path to configuration file
        """
        print(f"\n🌍 Creating Virtual Observatory for {location_name}")
        print("=" * 60)

        # Step 1: Create configuration
        print("📝 Step 1: Creating configuration...")
        config = self.create_configuration(location_name, latitude, longitude, elevation)

        if interactive:
            # Allow user to modify key parameters
            print(f"\nCurrent magnetic declination estimate: {config['target_location']['magnetic_declination']:.1f}°")
            user_declination = input("Enter magnetic declination (or press Enter to keep estimate): ")
            if user_declination.strip():
                try:
                    config['target_location']['magnetic_declination'] = float(user_declination)
                except ValueError:
                    print("Invalid declination, keeping estimate")

        # Step 2: Analyze network
        print("🏗️  Step 2: Analyzing observatory network...")
        network, geometry = self.analyze_network(latitude, longitude)

        print(f"\nNearest observatories:")
        for i, obs in enumerate(network.nearest_four, 1):
            print(f"  {i}. {obs.code} - {obs.name} ({obs.distance_km:.0f} km)")

        print(f"\nNetwork geometry:")
        print(f"  Average distance: {geometry['average_distance_km']:.0f} km")
        print(f"  Network spread: {geometry['network_spread_km']:.0f} km")
        print(f"  Coverage area: {geometry['lat_span_degrees']:.1f}° × {geometry['lon_span_degrees']:.1f}°")

        # Check network quality
        if geometry['average_distance_km'] > 1500:
            print("  ⚠️  WARNING: Large average distance may reduce accuracy")
        elif geometry['average_distance_km'] < 500:
            print("  ✅ Excellent network proximity")
        else:
            print("  ✅ Good network coverage")

        # Step 3: Test interpolation
        print("🧪 Step 3: Testing interpolation methods...")
        test_results = self.test_interpolation(network, location_name)

        successful_methods = [method for method, result in test_results.items() if result['success']]

        if not successful_methods:
            print("  ❌ No interpolation methods succeeded")
            return None

        print(f"\nInterpolation test results:")
        for method, result in test_results.items():
            if result['success']:
                print(f"  {method:10s}: {result['magnitude']:5.1f} μT (Quality: {result['quality']:.3f})")
            else:
                print(f"  {method:10s}: FAILED - {result['error']}")

        # Recommend best method
        best_method = max(
            [(method, result) for method, result in test_results.items() if result['success']],
            key=lambda x: x[1]['quality']
        )
        print(f"\n  🏆 Recommended method: {best_method[0]} (Quality: {best_method[1]['quality']:.3f})")
        config['interpolation']['method'] = best_method[0].lower()

        # Step 4: Save configuration
        print("💾 Step 4: Saving configuration...")
        config_path = self.save_configuration(config, location_name)
        print(f"Configuration saved to: {config_path}")

        # Step 5: Generate usage example
        print("📋 Step 5: Generating usage example...")
        self.generate_usage_example(config_path, location_name, best_method[1]['magnitude'])

        print(f"\n✅ Virtual Observatory created successfully!")
        print(f"   Location: {location_name} ({latitude:.4f}°, {longitude:.4f}°)")
        print(f"   Configuration: {config_path}")
        print(f"   Predicted field: {best_method[1]['magnitude']:.1f} μT")
        print(f"   Best method: {best_method[0]}")

        return config_path

    def generate_usage_example(self, config_path: str, location_name: str,
                             predicted_magnitude: float):
        """Generate usage example script for the new observatory."""

        example_script = f'''#!/usr/bin/env python3
"""
Usage Example: {location_name} Virtual Observatory
Generated automatically by create_virtual_observatory.py
"""

from virtual_observatory.virtual_station_predictor import VirtualObservatoryPredictor
import numpy as np

def main():
    print("🌍 {location_name} Virtual Observatory Demo")
    print("=" * 50)

    # Initialize virtual observatory
    predictor = VirtualObservatoryPredictor(config_file="{config_path}")

    # Display network information
    predictor.network.print_network_summary()

    # Simulate USGS data (replace with real data collection)
    simulated_usgs_data = {{
        obs.code: np.array([55e-6, 2e-6, 54e-6]) * (1 + np.random.normal(0, 0.01))
        for obs in predictor.network.nearest_four
    }}

    # Generate prediction
    result = predictor.interpolator.inverse_distance_weighting(simulated_usgs_data)
    quality = predictor.interpolator.get_interpolation_quality_score(result)

    print(f"\\n{location_name} Virtual Observatory Reading:")
    print(f"  Magnitude: {{result.magnitude*1e6:.1f}} μT")
    print(f"  Components: X={{result.x_component*1e6:.1f}}, Y={{result.y_component*1e6:.1f}}, Z={{result.z_component*1e6:.1f}} μT")
    print(f"  Quality Score: {{quality:.3f}}")
    print(f"  Uncertainty: ±{{result.uncertainty_mag*1e6:.1f}} μT")

    # Expected magnitude for validation
    print(f"\\nExpected magnitude: ~{predicted_magnitude:.1f} μT")

if __name__ == "__main__":
    main()
'''

        # Save example script
        safe_name = location_name.lower().replace(" ", "_").replace(",", "").replace(".", "")
        example_path = f"example_{safe_name}_virtual_observatory.py"

        with open(example_path, 'w') as f:
            f.write(example_script)

        os.chmod(example_path, 0o755)  # Make executable
        print(f"Usage example saved to: {example_path}")

    def interactive_setup(self):
        """Interactive setup process."""
        print("🌍 Interactive Virtual Observatory Setup")
        print("=" * 45)

        # Get location information
        location_name = input("Enter location name (e.g., 'Fairbanks, Alaska'): ").strip()
        if not location_name:
            print("Location name is required")
            return None

        try:
            latitude = float(input("Enter latitude (decimal degrees): "))
            longitude = float(input("Enter longitude (decimal degrees): "))
        except ValueError:
            print("Invalid coordinates")
            return None

        elevation_input = input("Enter elevation in meters (optional, press Enter for 0): ").strip()
        elevation = float(elevation_input) if elevation_input else 0.0

        # Create observatory
        return self.create_virtual_observatory(location_name, latitude, longitude, elevation, interactive=True)


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description='Create Virtual Geomagnetic Observatory')
    parser.add_argument('--location', type=str, help='Location name (e.g., "Fairbanks, Alaska")')
    parser.add_argument('--lat', type=float, help='Latitude in decimal degrees')
    parser.add_argument('--lon', type=float, help='Longitude in decimal degrees')
    parser.add_argument('--elevation', type=float, default=0.0, help='Elevation in meters (default: 0)')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')

    args = parser.parse_args()

    setup = VirtualObservatorySetup()

    if args.interactive:
        # Interactive mode
        config_path = setup.interactive_setup()
    elif args.location and args.lat is not None and args.lon is not None:
        # Command line mode
        config_path = setup.create_virtual_observatory(
            args.location, args.lat, args.lon, args.elevation
        )
    else:
        # Show help and examples
        print("Virtual Observatory Creation Tool")
        print("=" * 35)
        print("\nUsage Examples:")
        print("  Interactive mode:")
        print("    ./venv/bin/python create_virtual_observatory.py --interactive")
        print("\n  Command line mode:")
        print("    ./venv/bin/python create_virtual_observatory.py --location 'Fairbanks, Alaska' --lat 64.8378 --lon -147.7164")
        print("    ./venv/bin/python create_virtual_observatory.py --location 'Reykjavik, Iceland' --lat 64.1466 --lon -21.9426 --elevation 100")
        print("\n  See VIRTUAL_OBSERVATORY_GUIDE.md for complete documentation")
        return 1

    if config_path:
        print(f"\n📖 Next steps:")
        print(f"   1. Review configuration: {config_path}")
        print(f"   2. Run the generated example script")
        print(f"   3. Create plots: ./venv/bin/python virtual_observatory_plotter.py")
        print(f"   4. See VIRTUAL_OBSERVATORY_GUIDE.md for advanced usage")
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())