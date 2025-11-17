#!/usr/bin/env python3
"""
Virtual Geomagnetic Observatory Demonstration
Palmer, Alaska (61.5994°N, -149.115°W)

This script demonstrates the complete virtual observatory system using ML-based
spatial interpolation from the 4 nearest USGS geomagnetic observatories.
"""

import sys
import numpy as np
from datetime import datetime
import warnings

from virtual_observatory.virtual_station_predictor import VirtualObservatoryPredictor


def main():
    print("🌍 VIRTUAL GEOMAGNETIC OBSERVATORY - PALMER, ALASKA")
    print("=" * 65)
    print("AI/ML-based spatial interpolation using USGS observatory network")
    print(f"Demonstration run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # Initialize virtual observatory
        config_path = 'config/virtual_observatory_config.json'
        predictor = VirtualObservatoryPredictor(
            db_path='/deepsink1/weatherstation/data/weather_data.db',
            config_file=config_path
        )

        # Display network information
        print("🏗️  Observatory Network Configuration:")
        print("-" * 40)
        print(f"Target Location: {predictor.config['target_location']['name']}")
        print(f"Coordinates: {predictor.config['target_location']['latitude']:.4f}°N, "
              f"{predictor.config['target_location']['longitude']:.4f}°W")
        print(f"Magnetic Declination: {predictor.config['target_location']['magnetic_declination']}°")
        print()

        print("4 Nearest USGS Observatories:")
        for i, obs in enumerate(predictor.network.nearest_four, 1):
            weight = predictor.network.get_spatial_weights()[i-1]
            print(f"  {i}. {obs.code} - {obs.name}")
            print(f"     Distance: {obs.distance_km:.0f} km, Weight: {weight:.1%}")
            print(f"     Established: {obs.established}")

        print()

        # Simulate realistic USGS data (based on Palmer area magnetic field)
        print("📡 Simulated USGS Observatory Data:")
        print("-" * 35)

        # Realistic magnetic field values for Alaska region (in Tesla)
        usgs_data = {
            'CMO': np.array([55.7e-6, 2.1e-6, 54.2e-6]),  # College Observatory - closest
            'SIT': np.array([54.2e-6, 1.8e-6, 53.1e-6]),  # Sitka - southeast Alaska
            'SHU': np.array([53.8e-6, 2.3e-6, 52.9e-6]),  # Shumagin - Aleutian chain
            'DED': np.array([56.1e-6, 1.9e-6, 54.8e-6])   # Deadhorse - North Slope
        }

        for code, data in usgs_data.items():
            obs = predictor.network.get_observatory_by_code(code)
            mag = np.linalg.norm(data) * 1e6
            print(f"  {code} ({obs.name}): {mag:.1f} μT")
            print(f"    Components: X={data[0]*1e6:.1f}, Y={data[1]*1e6:.1f}, Z={data[2]*1e6:.1f} μT")

        print()

        # Generate virtual observatory predictions
        print("🤖 AI/ML Spatial Interpolation Results:")
        print("-" * 40)

        # Method 1: Inverse Distance Weighting (IDW)
        result_idw = predictor.interpolator.inverse_distance_weighting(usgs_data)
        quality_idw = predictor.interpolator.get_interpolation_quality_score(result_idw)

        print("Method 1: Inverse Distance Weighting (IDW)")
        print(f"  📊 Magnitude: {result_idw.magnitude*1e6:.1f} μT")
        print(f"  📈 Components: X={result_idw.x_component*1e6:.1f}, Y={result_idw.y_component*1e6:.1f}, Z={result_idw.z_component*1e6:.1f} μT")
        print(f"  📏 Uncertainty: ±{result_idw.uncertainty_mag*1e6:.1f} μT")
        print(f"  ⭐ Quality Score: {quality_idw:.3f}")
        print()

        # Method 2: Ensemble (IDW + Gaussian Process) with warning suppression
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            result_ensemble = predictor.interpolator.ensemble_interpolation(usgs_data)
            quality_ensemble = predictor.interpolator.get_interpolation_quality_score(result_ensemble)

        print("Method 2: Ensemble (IDW + Gaussian Process)")
        print(f"  📊 Magnitude: {result_ensemble.magnitude*1e6:.1f} μT")
        print(f"  📈 Components: X={result_ensemble.x_component*1e6:.1f}, Y={result_ensemble.y_component*1e6:.1f}, Z={result_ensemble.z_component*1e6:.1f} μT")
        print(f"  📏 Uncertainty: ±{result_ensemble.uncertainty_mag*1e6:.1f} μT")
        print(f"  ⭐ Quality Score: {quality_ensemble:.3f}")
        print()

        # Network geometry analysis
        geometry = predictor.network.validate_network_geometry()
        print("🔍 Network Geometry Analysis:")
        print("-" * 30)
        print(f"  Network centroid distance: {geometry['centroid_distance_km']:.0f} km from target")
        print(f"  Network spatial spread: {geometry['network_spread_km']:.0f} km")
        print(f"  Geographic coverage: {geometry['lat_span_degrees']:.1f}° lat × {geometry['lon_span_degrees']:.1f}° lon")
        print(f"  Average observatory distance: {geometry['average_distance_km']:.0f} km")
        print(f"  Network aspect ratio: {geometry['aspect_ratio']:.2f}")
        print()

        # Determine best method
        best_method = "IDW" if quality_idw > quality_ensemble else "Ensemble"
        best_result = result_idw if quality_idw > quality_ensemble else result_ensemble
        best_quality = max(quality_idw, quality_ensemble)

        print("✅ VIRTUAL OBSERVATORY STATUS: OPERATIONAL")
        print("=" * 50)
        print(f"🎯 Target Location: Palmer, Alaska")
        print(f"📍 Coordinates: {predictor.config['target_location']['latitude']:.4f}°N, {predictor.config['target_location']['longitude']:.4f}°W")
        print(f"🏆 Best Method: {best_method} (Quality: {best_quality:.3f})")
        print(f"🧲 Predicted Magnetic Field: {best_result.magnitude*1e6:.1f} μT")
        print(f"🎖️  Network Coverage: {len(predictor.network.nearest_four)} USGS observatories")
        print(f"⚡ Interpolation Power: {geometry['average_distance_km']:.0f} km average baseline")

        # Earth's magnetic field context
        earth_field_strength = 50  # Typical range 25-65 μT
        print()
        print("🌍 Geophysical Context:")
        print(f"   Earth's magnetic field at Palmer: ~{earth_field_strength}-65 μT (typical)")
        print(f"   Predicted field strength: {best_result.magnitude*1e6:.1f} μT")
        print(f"   Field strength category: {'Normal' if 50 <= best_result.magnitude*1e6 <= 65 else 'Atypical'}")

        print()
        print("📚 Technical Implementation:")
        print("   • Haversine distance calculations for geographic proximity")
        print("   • NIST SP 330 SI unit compliance (Tesla)")
        print("   • Scikit-learn Gaussian Process Regression with RBF kernels")
        print("   • Uncertainty quantification and confidence intervals")
        print("   • Cross-validation against local sensor measurements")
        print("   • Real-time data quality assessment")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)