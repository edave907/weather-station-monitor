#!/usr/bin/env python3
"""
Usage Example: Fairbanks, Alaska Virtual Observatory
Generated automatically by create_virtual_observatory.py
"""

from virtual_observatory.virtual_station_predictor import VirtualObservatoryPredictor
import numpy as np

def main():
    print("🌍 Fairbanks, Alaska Virtual Observatory Demo")
    print("=" * 50)

    # Initialize virtual observatory
    predictor = VirtualObservatoryPredictor(config_file="config/virtual_observatory_fairbanks_alaska_config.json")

    # Display network information
    predictor.network.print_network_summary()

    # Simulate USGS data (replace with real data collection)
    simulated_usgs_data = {
        obs.code: np.array([55e-6, 2e-6, 54e-6]) * (1 + np.random.normal(0, 0.01))
        for obs in predictor.network.nearest_four
    }

    # Generate prediction
    result = predictor.interpolator.inverse_distance_weighting(simulated_usgs_data)
    quality = predictor.interpolator.get_interpolation_quality_score(result)

    print(f"\nFairbanks, Alaska Virtual Observatory Reading:")
    print(f"  Magnitude: {result.magnitude*1e6:.1f} μT")
    print(f"  Components: X={result.x_component*1e6:.1f}, Y={result.y_component*1e6:.1f}, Z={result.z_component*1e6:.1f} μT")
    print(f"  Quality Score: {quality:.3f}")
    print(f"  Uncertainty: ±{result.uncertainty_mag*1e6:.1f} μT")

    # Expected magnitude for validation
    print(f"\nExpected magnitude: ~891.4 μT")

if __name__ == "__main__":
    main()
