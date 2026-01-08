#!/usr/bin/env python3
"""
Scientific Validation Test for Synthetic Observatories
Leave-One-Out Cross-Validation Using USGS Observatory Network

This script implements rigorous scientific testing of the synthetic observatory
concept by:
1. Randomly selecting 5 USGS observatories from the 14 available
2. Randomly selecting 1 as the "test" observatory
3. Using the remaining 4 to create a synthetic observatory at the test location
4. Comparing synthetic predictions with actual test observatory "measurements"
5. Repeating the process multiple times for statistical significance

Note: Since we don't have access to real USGS data feeds, this simulation
uses realistic magnetic field values based on each observatory's geographic
location and known geomagnetic characteristics.
"""

import numpy as np
import random
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import pandas as pd
from dataclasses import dataclass

from virtual_observatory.observatory_network import ObservatoryNetwork, Observatory
from virtual_observatory.spatial_interpolation import SpatialInterpolator, InterpolationResult


@dataclass
class ValidationResult:
    """Results of a single validation test."""
    test_observatory: str
    training_observatories: List[str]
    actual_field: np.ndarray
    predicted_field: np.ndarray
    magnitude_error: float
    component_errors: np.ndarray
    inclination_error: float
    declination_error: float
    quality_score: float
    distance_to_nearest: float
    network_spread: float


class ScientificValidationTest:
    """Scientific validation testing framework for synthetic observatories."""

    def __init__(self, random_seed: int = 42):
        """Initialize the validation test framework."""
        self.random_seed = random_seed
        random.seed(random_seed)
        np.random.seed(random_seed)

        # Get all USGS observatories
        self.all_observatories = self._get_all_usgs_observatories()

        # Validation results storage
        self.validation_results: List[ValidationResult] = []

    def _get_all_usgs_observatories(self) -> Dict[str, Observatory]:
        """Get complete USGS observatory network."""
        # Create a network to access all observatories
        network = ObservatoryNetwork()
        return network.observatories

    def _generate_realistic_magnetic_field(self, obs: Observatory) -> np.ndarray:
        """
        Generate realistic magnetic field values for an observatory location.

        This simulates what real USGS data might look like based on:
        - Geographic location (latitude/longitude effects)
        - Known geomagnetic field characteristics
        - Typical field strengths for different regions

        Args:
            obs: Observatory for which to generate field data

        Returns:
            3-component magnetic field vector in Tesla
        """
        # Base field strength depends on latitude (stronger at poles)
        lat_factor = 1.0 + 0.3 * abs(obs.latitude) / 90.0

        # Typical field components for North America
        if obs.latitude > 65:  # High Arctic (Alaska north)
            base_field = np.array([55.0e-6, 1.2e-6, 54.0e-6]) * lat_factor
        elif obs.latitude > 55:  # Sub-Arctic (most of Alaska)
            base_field = np.array([54.5e-6, 1.8e-6, 53.5e-6]) * lat_factor
        elif obs.latitude > 45:  # Northern states/southern Canada
            base_field = np.array([52.0e-6, 2.5e-6, 51.0e-6]) * lat_factor
        elif obs.latitude > 35:  # Mid-latitude US
            base_field = np.array([50.0e-6, 3.0e-6, 48.0e-6]) * lat_factor
        elif obs.latitude > 25:  # Southern US
            base_field = np.array([48.0e-6, 3.5e-6, 45.0e-6]) * lat_factor
        else:  # Tropical (Hawaii, territories)
            base_field = np.array([45.0e-6, 4.0e-6, 42.0e-6]) * lat_factor

        # Add longitude-dependent variations
        lon_variation = 0.02 * np.sin(np.radians(obs.longitude + 120))
        base_field *= (1.0 + lon_variation)

        # Add small random variations to simulate real measurement noise
        noise = np.random.normal(0, 0.5e-6, 3)  # ±0.5 μT noise

        # Add small systematic variations based on observatory characteristics
        if 'Alaska' in obs.description or obs.code in ['CMO', 'SIT', 'BRW', 'DED', 'SHU']:
            # Alaska has more complex magnetic field due to auroral activity
            auroral_noise = np.random.normal(0, 0.2e-6, 3)
            noise += auroral_noise

        return base_field + noise

    def run_single_validation(self, test_obs_code: str, training_obs_codes: List[str]) -> ValidationResult:
        """
        Run a single validation test.

        Args:
            test_obs_code: Code of observatory to use as test target
            training_obs_codes: Codes of observatories to use for training

        Returns:
            ValidationResult containing all metrics
        """
        # Get observatory objects
        test_obs = self.all_observatories[test_obs_code]

        print(f"\n🧪 Testing synthetic observatory at {test_obs.name} ({test_obs_code})")
        print(f"   Location: {test_obs.latitude:.2f}°N, {test_obs.longitude:.2f}°W")
        print(f"   Training network: {training_obs_codes}")

        # Generate "actual" field at test location
        actual_field = self._generate_realistic_magnetic_field(test_obs)

        # Create network using only training observatories
        # We'll manually override the nearest_four selection
        network = ObservatoryNetwork(target_lat=test_obs.latitude, target_lon=test_obs.longitude)

        # Override the network to use only our training observatories
        training_obs = [self.all_observatories[code] for code in training_obs_codes]

        # Calculate distances from test location to training observatories
        for obs in training_obs:
            obs.distance_km = network.haversine_distance(
                test_obs.latitude, test_obs.longitude,
                obs.latitude, obs.longitude
            )

        # Sort by distance and use as network
        training_obs.sort(key=lambda x: x.distance_km)
        network.nearest_four = training_obs

        print(f"   Training distances: {[f'{obs.code}:{obs.distance_km:.0f}km' for obs in training_obs]}")

        # Generate training data
        training_data = {}
        for obs in training_obs:
            training_data[obs.code] = self._generate_realistic_magnetic_field(obs)

        # Create interpolator and make prediction
        interpolator = SpatialInterpolator(network)

        # Test all interpolation methods
        try:
            result_idw = interpolator.inverse_distance_weighting(training_data)
            quality_idw = interpolator.get_interpolation_quality_score(result_idw)
            print(f"   IDW: {result_idw.magnitude*1e6:.1f} μT (Quality: {quality_idw:.3f})")
        except Exception as e:
            print(f"   IDW failed: {e}")
            result_idw = None
            quality_idw = 0

        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                result_gp = interpolator.gaussian_process_interpolation(training_data)
                quality_gp = interpolator.get_interpolation_quality_score(result_gp)
                print(f"   GP:  {result_gp.magnitude*1e6:.1f} μT (Quality: {quality_gp:.3f})")
        except Exception as e:
            print(f"   GP failed: {e}")
            result_gp = None
            quality_gp = 0

        # Choose best method
        if quality_idw >= quality_gp and result_idw is not None:
            predicted_result = result_idw
            best_quality = quality_idw
            best_method = "IDW"
        elif result_gp is not None:
            predicted_result = result_gp
            best_quality = quality_gp
            best_method = "GP"
        else:
            raise Exception("All interpolation methods failed")

        predicted_field = np.array([predicted_result.x_component, predicted_result.y_component, predicted_result.z_component])

        # Calculate errors
        magnitude_error = abs(predicted_result.magnitude - np.linalg.norm(actual_field))
        component_errors = np.abs(predicted_field - actual_field)

        # Calculate inclination and declination errors
        actual_h = np.sqrt(actual_field[0]**2 + actual_field[1]**2)
        predicted_h = np.sqrt(predicted_field[0]**2 + predicted_field[1]**2)

        actual_inclination = np.degrees(np.arctan2(actual_field[2], actual_h))
        predicted_inclination = np.degrees(np.arctan2(predicted_field[2], predicted_h))
        inclination_error = abs(predicted_inclination - actual_inclination)

        actual_declination = np.degrees(np.arctan2(actual_field[1], actual_field[0]))
        predicted_declination = np.degrees(np.arctan2(predicted_field[1], predicted_field[0]))
        declination_error = abs(predicted_declination - actual_declination)
        if declination_error > 180:
            declination_error = 360 - declination_error

        # Network geometry metrics
        distances = [obs.distance_km for obs in training_obs]
        distance_to_nearest = min(distances)
        network_spread = np.std(distances)

        # Results summary
        print(f"   Best method: {best_method}")
        print(f"   Actual:    {np.linalg.norm(actual_field)*1e6:.1f} μT, Inc: {actual_inclination:.1f}°")
        print(f"   Predicted: {predicted_result.magnitude*1e6:.1f} μT, Inc: {predicted_inclination:.1f}°")
        print(f"   Magnitude error: {magnitude_error*1e6:.1f} μT ({magnitude_error/np.linalg.norm(actual_field)*100:.1f}%)")
        print(f"   Inclination error: {inclination_error:.1f}°")

        return ValidationResult(
            test_observatory=test_obs_code,
            training_observatories=training_obs_codes,
            actual_field=actual_field,
            predicted_field=predicted_field,
            magnitude_error=magnitude_error,
            component_errors=component_errors,
            inclination_error=inclination_error,
            declination_error=declination_error,
            quality_score=best_quality,
            distance_to_nearest=distance_to_nearest,
            network_spread=network_spread
        )

    def run_random_validation_suite(self, num_tests: int = 10) -> List[ValidationResult]:
        """
        Run multiple random validation tests.

        Args:
            num_tests: Number of random tests to perform

        Returns:
            List of validation results
        """
        print("🔬 SCIENTIFIC VALIDATION OF SYNTHETIC OBSERVATORIES")
        print("="*60)
        print(f"Conducting {num_tests} random cross-validation tests")
        print(f"Random seed: {self.random_seed}")

        results = []

        for test_num in range(num_tests):
            print(f"\n📋 Test {test_num + 1}/{num_tests}")
            print("-" * 30)

            # Step 1: Randomly select 5 observatories from 14
            available_obs = list(self.all_observatories.keys())
            selected_5 = random.sample(available_obs, 5)
            print(f"Selected 5 observatories: {selected_5}")

            # Step 2: Randomly select 1 as test, remaining 4 as training
            test_obs = random.choice(selected_5)
            training_obs = [obs for obs in selected_5 if obs != test_obs]

            # Run validation
            try:
                result = self.run_single_validation(test_obs, training_obs)
                results.append(result)
            except Exception as e:
                print(f"   ❌ Test failed: {e}")
                continue

        self.validation_results = results
        return results

    def analyze_results(self) -> Dict:
        """Analyze validation results and compute statistics."""
        if not self.validation_results:
            raise ValueError("No validation results available")

        print("\n📊 VALIDATION RESULTS ANALYSIS")
        print("="*40)

        # Extract metrics
        magnitude_errors = [r.magnitude_error * 1e6 for r in self.validation_results]  # Convert to μT
        inclination_errors = [r.inclination_error for r in self.validation_results]
        declination_errors = [r.declination_error for r in self.validation_results]
        quality_scores = [r.quality_score for r in self.validation_results]
        nearest_distances = [r.distance_to_nearest for r in self.validation_results]

        # Calculate relative errors
        magnitude_relative_errors = []
        for r in self.validation_results:
            actual_mag = np.linalg.norm(r.actual_field) * 1e6
            relative_error = (r.magnitude_error * 1e6 / actual_mag) * 100
            magnitude_relative_errors.append(relative_error)

        # Statistics
        stats = {
            'num_tests': len(self.validation_results),
            'magnitude_error_mean': np.mean(magnitude_errors),
            'magnitude_error_std': np.std(magnitude_errors),
            'magnitude_error_median': np.median(magnitude_errors),
            'magnitude_relative_error_mean': np.mean(magnitude_relative_errors),
            'magnitude_relative_error_std': np.std(magnitude_relative_errors),
            'inclination_error_mean': np.mean(inclination_errors),
            'inclination_error_std': np.std(inclination_errors),
            'declination_error_mean': np.mean(declination_errors),
            'declination_error_std': np.std(declination_errors),
            'quality_score_mean': np.mean(quality_scores),
            'quality_score_std': np.std(quality_scores),
            'distance_mean': np.mean(nearest_distances),
            'distance_std': np.std(nearest_distances)
        }

        # Print summary
        print(f"Number of successful tests: {stats['num_tests']}")
        print(f"\nMagnitude Errors:")
        print(f"  Mean: {stats['magnitude_error_mean']:.1f} ± {stats['magnitude_error_std']:.1f} μT")
        print(f"  Median: {stats['magnitude_error_median']:.1f} μT")
        print(f"  Relative: {stats['magnitude_relative_error_mean']:.1f} ± {stats['magnitude_relative_error_std']:.1f} %")

        print(f"\nDirectional Errors:")
        print(f"  Inclination: {stats['inclination_error_mean']:.1f} ± {stats['inclination_error_std']:.1f} degrees")
        print(f"  Declination: {stats['declination_error_mean']:.1f} ± {stats['declination_error_std']:.1f} degrees")

        print(f"\nQuality and Distance:")
        print(f"  Quality Score: {stats['quality_score_mean']:.3f} ± {stats['quality_score_std']:.3f}")
        print(f"  Average Distance to Nearest: {stats['distance_mean']:.0f} ± {stats['distance_std']:.0f} km")

        # Performance assessment
        print(f"\nPerformance Assessment:")
        excellent_tests = sum(1 for e in magnitude_relative_errors if e < 5)
        good_tests = sum(1 for e in magnitude_relative_errors if 5 <= e < 15)
        poor_tests = sum(1 for e in magnitude_relative_errors if e >= 15)

        print(f"  Excellent (<5% error): {excellent_tests}/{stats['num_tests']} ({excellent_tests/stats['num_tests']*100:.0f}%)")
        print(f"  Good (5-15% error): {good_tests}/{stats['num_tests']} ({good_tests/stats['num_tests']*100:.0f}%)")
        print(f"  Poor (>15% error): {poor_tests}/{stats['num_tests']} ({poor_tests/stats['num_tests']*100:.0f}%)")

        return stats

    def create_validation_plots(self, save_path: str = None):
        """Create visualization plots of validation results."""
        if not self.validation_results:
            raise ValueError("No validation results available")

        # Create figure with subplots
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('Scientific Validation of Synthetic Observatories\nLeave-One-Out Cross-Validation Results',
                    fontsize=14, fontweight='bold')

        # Plot 1: Magnitude Error vs Distance
        ax1 = axes[0, 0]
        distances = [r.distance_to_nearest for r in self.validation_results]
        mag_errors = [r.magnitude_error * 1e6 for r in self.validation_results]

        ax1.scatter(distances, mag_errors, alpha=0.7, s=50)
        ax1.set_xlabel('Distance to Nearest Observatory (km)')
        ax1.set_ylabel('Magnitude Error (μT)')
        ax1.set_title('Magnitude Error vs Distance')
        ax1.grid(True, alpha=0.3)

        # Add trend line
        z = np.polyfit(distances, mag_errors, 1)
        p = np.poly1d(z)
        x_trend = np.linspace(min(distances), max(distances), 100)
        ax1.plot(x_trend, p(x_trend), "r--", alpha=0.8, label=f'Trend: {z[0]:.3f}x + {z[1]:.1f}')
        ax1.legend()

        # Plot 2: Inclination Error Distribution
        ax2 = axes[0, 1]
        inc_errors = [r.inclination_error for r in self.validation_results]
        ax2.hist(inc_errors, bins=8, alpha=0.7, edgecolor='black')
        ax2.set_xlabel('Inclination Error (degrees)')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Inclination Error Distribution')
        ax2.axvline(np.mean(inc_errors), color='red', linestyle='--', label=f'Mean: {np.mean(inc_errors):.1f}°')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Plot 3: Quality Score vs Error
        ax3 = axes[0, 2]
        quality_scores = [r.quality_score for r in self.validation_results]
        relative_errors = [(r.magnitude_error * 1e6 / np.linalg.norm(r.actual_field) / 1e6) * 100 for r in self.validation_results]

        ax3.scatter(quality_scores, relative_errors, alpha=0.7, s=50)
        ax3.set_xlabel('Quality Score')
        ax3.set_ylabel('Relative Magnitude Error (%)')
        ax3.set_title('Quality Score vs Error')
        ax3.grid(True, alpha=0.3)

        # Plot 4: Actual vs Predicted Magnitude
        ax4 = axes[1, 0]
        actual_mags = [np.linalg.norm(r.actual_field) * 1e6 for r in self.validation_results]
        predicted_mags = [np.linalg.norm(r.predicted_field) * 1e6 for r in self.validation_results]

        ax4.scatter(actual_mags, predicted_mags, alpha=0.7, s=50)

        # Perfect prediction line
        min_mag, max_mag = min(actual_mags), max(actual_mags)
        ax4.plot([min_mag, max_mag], [min_mag, max_mag], 'r--', label='Perfect Prediction')

        ax4.set_xlabel('Actual Magnitude (μT)')
        ax4.set_ylabel('Predicted Magnitude (μT)')
        ax4.set_title('Actual vs Predicted Magnitude')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        # Plot 5: Observatory Performance
        ax5 = axes[1, 1]
        test_obs_codes = [r.test_observatory for r in self.validation_results]
        obs_errors = {}

        for result in self.validation_results:
            obs = result.test_observatory
            error = (result.magnitude_error * 1e6 / np.linalg.norm(result.actual_field) / 1e6) * 100
            if obs not in obs_errors:
                obs_errors[obs] = []
            obs_errors[obs].append(error)

        obs_names = list(obs_errors.keys())
        obs_mean_errors = [np.mean(obs_errors[obs]) for obs in obs_names]

        bars = ax5.bar(range(len(obs_names)), obs_mean_errors, alpha=0.7)
        ax5.set_xlabel('Test Observatory')
        ax5.set_ylabel('Mean Relative Error (%)')
        ax5.set_title('Performance by Observatory')
        ax5.set_xticks(range(len(obs_names)))
        ax5.set_xticklabels(obs_names, rotation=45)
        ax5.grid(True, alpha=0.3)

        # Color bars by performance
        for i, bar in enumerate(bars):
            if obs_mean_errors[i] < 5:
                bar.set_color('green')
            elif obs_mean_errors[i] < 15:
                bar.set_color('orange')
            else:
                bar.set_color('red')

        # Plot 6: Error Summary
        ax6 = axes[1, 2]

        # Create summary statistics
        summary_data = {
            'Magnitude\n(μT)': [np.mean(mag_errors), np.std(mag_errors)],
            'Inclination\n(deg)': [np.mean(inc_errors), np.std(inc_errors)],
            'Relative\n(%)': [np.mean(relative_errors), np.std(relative_errors)],
            'Quality': [np.mean(quality_scores), np.std(quality_scores)]
        }

        categories = list(summary_data.keys())
        means = [summary_data[cat][0] for cat in categories]
        stds = [summary_data[cat][1] for cat in categories]

        x_pos = np.arange(len(categories))
        bars = ax6.bar(x_pos, means, yerr=stds, capsize=5, alpha=0.7)
        ax6.set_ylabel('Value')
        ax6.set_title('Error Summary (Mean ± Std)')
        ax6.set_xticks(x_pos)
        ax6.set_xticklabels(categories)
        ax6.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save plot
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"\nValidation plots saved to: {save_path}")
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_path = f'scientific_validation_{timestamp}.png'
            plt.savefig(default_path, dpi=300, bbox_inches='tight')
            print(f"\nValidation plots saved to: {default_path}")

        plt.show()

    def detailed_test_report(self):
        """Generate detailed test report."""
        if not self.validation_results:
            raise ValueError("No validation results available")

        print("\n📋 DETAILED TEST REPORT")
        print("="*50)

        for i, result in enumerate(self.validation_results, 1):
            test_obs = self.all_observatories[result.test_observatory]

            actual_mag = np.linalg.norm(result.actual_field) * 1e6
            predicted_mag = np.linalg.norm(result.predicted_field) * 1e6
            relative_error = (result.magnitude_error * 1e6 / actual_mag) * 100

            print(f"\nTest {i}: {result.test_observatory} - {test_obs.name}")
            print(f"  Location: {test_obs.latitude:.2f}°N, {test_obs.longitude:.2f}°W")
            print(f"  Training network: {result.training_observatories}")
            print(f"  Distance to nearest: {result.distance_to_nearest:.0f} km")
            print(f"  Network spread: {result.network_spread:.0f} km")
            print(f"  Actual magnitude: {actual_mag:.1f} μT")
            print(f"  Predicted magnitude: {predicted_mag:.1f} μT")
            print(f"  Magnitude error: {result.magnitude_error*1e6:.1f} μT ({relative_error:.1f}%)")
            print(f"  Inclination error: {result.inclination_error:.1f}°")
            print(f"  Declination error: {result.declination_error:.1f}°")
            print(f"  Quality score: {result.quality_score:.3f}")

            # Performance assessment
            if relative_error < 5:
                performance = "🟢 EXCELLENT"
            elif relative_error < 15:
                performance = "🟡 GOOD"
            else:
                performance = "🔴 POOR"
            print(f"  Performance: {performance}")


def main():
    """Run the scientific validation test."""
    print("🔬 SCIENTIFIC VALIDATION OF SYNTHETIC GEOMAGNETIC OBSERVATORIES")
    print("="*70)
    print("This test validates the synthetic observatory concept using")
    print("leave-one-out cross-validation with the USGS observatory network.")
    print()

    # Initialize validation test
    validator = ScientificValidationTest(random_seed=42)

    # Run validation suite
    results = validator.run_random_validation_suite(num_tests=15)

    if not results:
        print("❌ No successful tests completed")
        return

    # Analyze results
    stats = validator.analyze_results()

    # Generate detailed report
    validator.detailed_test_report()

    # Create plots
    validator.create_validation_plots()

    # Final assessment
    print("\n🎯 FINAL ASSESSMENT")
    print("="*25)

    mean_error = stats['magnitude_relative_error_mean']
    if mean_error < 5:
        assessment = "🟢 EXCELLENT - Synthetic observatories work very well"
    elif mean_error < 15:
        assessment = "🟡 GOOD - Synthetic observatories are useful for most applications"
    elif mean_error < 30:
        assessment = "🟠 FAIR - Synthetic observatories have limited accuracy"
    else:
        assessment = "🔴 POOR - Synthetic observatory concept needs improvement"

    print(f"Overall Performance: {assessment}")
    print(f"Mean Relative Error: {mean_error:.1f}%")
    print(f"Success Rate: {len(results)}/15 tests completed successfully")


if __name__ == "__main__":
    main()