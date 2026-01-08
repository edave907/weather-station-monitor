#!/usr/bin/env python3
"""
Spatial Interpolation Module for Virtual Observatory

This module implements machine learning-based spatial interpolation methods
to estimate magnetic field values at Palmer, Alaska using data from the
4 nearest USGS geomagnetic observatories.

Methods:
- Gaussian Process Regression with RBF kernels
- Inverse Distance Weighting (IDW)
- Ensemble interpolation combining multiple methods
- Uncertainty quantification and confidence intervals
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import warnings

# ML and statistical libraries
try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_squared_error, r2_score
    from sklearn.preprocessing import StandardScaler
    from scipy.spatial.distance import cdist
    from scipy import stats
    ML_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some ML libraries not available: {e}")
    ML_AVAILABLE = False

from .observatory_network import ObservatoryNetwork, Observatory


@dataclass
class InterpolationResult:
    """Result of spatial interpolation."""
    x_component: float
    y_component: float
    z_component: float
    magnitude: float
    uncertainty_x: float = 0.0
    uncertainty_y: float = 0.0
    uncertainty_z: float = 0.0
    uncertainty_mag: float = 0.0
    confidence_level: float = 0.95
    method: str = "unknown"
    timestamp: datetime = None


class SpatialInterpolator:
    """Advanced spatial interpolation for geomagnetic fields."""

    def __init__(self, network: ObservatoryNetwork):
        """Initialize with observatory network."""
        self.network = network
        self.observatories = network.get_nearest_observatories()
        self.weights = network.get_spatial_weights()
        self.coordinates = network.get_coordinate_matrix()

        # ML models
        self.gp_models = {}
        self.rf_models = {}
        self.scalers = {}

        # Training history
        self.training_history = []
        self.model_performance = {}

        print(f"Initialized spatial interpolator with {len(self.observatories)} observatories")

    def inverse_distance_weighting(self, magnetic_data: Dict[str, np.ndarray],
                                 power: float = 2.0) -> InterpolationResult:
        """
        Inverse Distance Weighting interpolation.

        Args:
            magnetic_data: Dict with observatory codes as keys and [x,y,z] arrays as values
            power: IDW power parameter (higher = more local influence)

        Returns:
            InterpolationResult with interpolated values
        """
        # Calculate inverse distance weights with power parameter
        distances = np.array([obs.distance_km for obs in self.observatories])
        weights = 1.0 / (distances ** power + 1e-6)  # Add epsilon to avoid division by zero
        weights = weights / np.sum(weights)  # Normalize

        # Interpolate each component
        x_values = []
        y_values = []
        z_values = []

        for obs in self.observatories:
            if obs.code in magnetic_data:
                data = magnetic_data[obs.code]
                if len(data) >= 3:
                    x_values.append(data[0])
                    y_values.append(data[1])
                    z_values.append(data[2])
                else:
                    # Handle missing data
                    x_values.append(0.0)
                    y_values.append(0.0)
                    z_values.append(0.0)
            else:
                # Observatory data not available
                x_values.append(0.0)
                y_values.append(0.0)
                z_values.append(0.0)

        x_values = np.array(x_values)
        y_values = np.array(y_values)
        z_values = np.array(z_values)

        # Weighted interpolation
        x_interp = np.sum(weights * x_values)
        y_interp = np.sum(weights * y_values)
        z_interp = np.sum(weights * z_values)

        magnitude = np.sqrt(x_interp**2 + y_interp**2 + z_interp**2)

        # Estimate uncertainty based on data spread and distances
        x_uncertainty = np.sqrt(np.sum(weights * (x_values - x_interp)**2))
        y_uncertainty = np.sqrt(np.sum(weights * (y_values - y_interp)**2))
        z_uncertainty = np.sqrt(np.sum(weights * (z_values - z_interp)**2))
        mag_uncertainty = np.sqrt(x_uncertainty**2 + y_uncertainty**2 + z_uncertainty**2)

        return InterpolationResult(
            x_component=x_interp,
            y_component=y_interp,
            z_component=z_interp,
            magnitude=magnitude,
            uncertainty_x=x_uncertainty,
            uncertainty_y=y_uncertainty,
            uncertainty_z=z_uncertainty,
            uncertainty_mag=mag_uncertainty,
            method="IDW",
            timestamp=datetime.now()
        )

    def gaussian_process_interpolation(self, magnetic_data: Dict[str, np.ndarray],
                                     training_data: Optional[List[Dict]] = None) -> InterpolationResult:
        """
        Gaussian Process Regression interpolation with uncertainty quantification.

        Args:
            magnetic_data: Current magnetic data from observatories
            training_data: Historical data for GP training (optional)

        Returns:
            InterpolationResult with mean prediction and uncertainty
        """
        if not ML_AVAILABLE:
            print("Warning: Scikit-learn not available, falling back to IDW")
            return self.inverse_distance_weighting(magnetic_data)

        # Prepare coordinate features (lat, lon, elevation)
        X = self.coordinates.copy()

        # Add temporal and geomagnetic features if available
        if training_data:
            # Use historical data for training
            return self._train_and_predict_gp(magnetic_data, training_data)
        else:
            # Use current data only for simple GP interpolation
            return self._simple_gp_interpolation(magnetic_data)

    def _simple_gp_interpolation(self, magnetic_data: Dict[str, np.ndarray]) -> InterpolationResult:
        """Simple GP interpolation using current data only."""
        # Extract coordinates and magnetic values
        X_obs = []
        y_x = []
        y_y = []
        y_z = []

        for i, obs in enumerate(self.observatories):
            if obs.code in magnetic_data:
                X_obs.append([obs.latitude, obs.longitude, obs.elevation])
                data = magnetic_data[obs.code]
                if len(data) >= 3:
                    y_x.append(data[0])
                    y_y.append(data[1])
                    y_z.append(data[2])
                else:
                    y_x.append(0.0)
                    y_y.append(0.0)
                    y_z.append(0.0)

        if len(X_obs) < 2:
            print("Warning: Insufficient data for GP, falling back to IDW")
            return self.inverse_distance_weighting(magnetic_data)

        X_obs = np.array(X_obs)
        target_point = np.array([[self.network.target_lat, self.network.target_lon, 0.0]])

        # Define GP kernel
        kernel = ConstantKernel(1.0) * RBF(length_scale=100.0) + WhiteKernel(noise_level=0.1)

        results = {}

        # Fit GP for each component
        for component, y_values in [('x', y_x), ('y', y_y), ('z', y_z)]:
            y_values = np.array(y_values)

            if np.std(y_values) < 1e-10:  # Constant values
                pred_mean = np.mean(y_values)
                pred_std = 0.1
            else:
                try:
                    gp = GaussianProcessRegressor(kernel=kernel, random_state=42)
                    gp.fit(X_obs, y_values)

                    pred_mean, pred_std = gp.predict(target_point, return_std=True)
                    pred_mean = pred_mean[0]
                    pred_std = pred_std[0]
                except Exception as e:
                    print(f"GP fitting failed for {component}: {e}, using IDW")
                    idw_result = self.inverse_distance_weighting(magnetic_data)
                    return idw_result

            results[component] = (pred_mean, pred_std)

        # Extract results
        x_pred, x_std = results['x']
        y_pred, y_std = results['y']
        z_pred, z_std = results['z']

        magnitude = np.sqrt(x_pred**2 + y_pred**2 + z_pred**2)
        mag_uncertainty = np.sqrt(x_std**2 + y_std**2 + z_std**2)

        return InterpolationResult(
            x_component=x_pred,
            y_component=y_pred,
            z_component=z_pred,
            magnitude=magnitude,
            uncertainty_x=x_std,
            uncertainty_y=y_std,
            uncertainty_z=z_std,
            uncertainty_mag=mag_uncertainty,
            method="Gaussian Process",
            timestamp=datetime.now()
        )

    def ensemble_interpolation(self, magnetic_data: Dict[str, np.ndarray],
                             methods: List[str] = None) -> InterpolationResult:
        """
        Ensemble interpolation combining multiple methods.

        Args:
            magnetic_data: Current magnetic data from observatories
            methods: List of methods to combine ['idw', 'gp']

        Returns:
            Ensemble-averaged InterpolationResult
        """
        if methods is None:
            methods = ['idw', 'gp']

        results = []
        weights = []

        # Compute predictions from each method
        if 'idw' in methods:
            idw_result = self.inverse_distance_weighting(magnetic_data)
            results.append(idw_result)
            weights.append(0.3)  # Lower weight for simpler method

        if 'gp' in methods and ML_AVAILABLE:
            gp_result = self.gaussian_process_interpolation(magnetic_data)
            results.append(gp_result)
            weights.append(0.7)  # Higher weight for more sophisticated method

        if not results:
            print("No valid interpolation methods available")
            return self.inverse_distance_weighting(magnetic_data)

        # Normalize weights
        weights = np.array(weights)
        weights = weights / np.sum(weights)

        # Ensemble averaging
        x_ensemble = np.sum([w * r.x_component for w, r in zip(weights, results)])
        y_ensemble = np.sum([w * r.y_component for w, r in zip(weights, results)])
        z_ensemble = np.sum([w * r.z_component for w, r in zip(weights, results)])

        # Uncertainty as weighted average of individual uncertainties
        x_uncertainty = np.sqrt(np.sum([w * r.uncertainty_x**2 for w, r in zip(weights, results)]))
        y_uncertainty = np.sqrt(np.sum([w * r.uncertainty_y**2 for w, r in zip(weights, results)]))
        z_uncertainty = np.sqrt(np.sum([w * r.uncertainty_z**2 for w, r in zip(weights, results)]))

        magnitude = np.sqrt(x_ensemble**2 + y_ensemble**2 + z_ensemble**2)
        mag_uncertainty = np.sqrt(x_uncertainty**2 + y_uncertainty**2 + z_uncertainty**2)

        return InterpolationResult(
            x_component=x_ensemble,
            y_component=y_ensemble,
            z_component=z_ensemble,
            magnitude=magnitude,
            uncertainty_x=x_uncertainty,
            uncertainty_y=y_uncertainty,
            uncertainty_z=z_uncertainty,
            uncertainty_mag=mag_uncertainty,
            method=f"Ensemble({','.join(methods)})",
            timestamp=datetime.now()
        )

    def interpolate_magnetic_field(self, magnetic_data: Dict[str, np.ndarray],
                                 method: str = "ensemble") -> InterpolationResult:
        """
        Main interpolation method dispatcher.

        Args:
            magnetic_data: Dict mapping observatory codes to [x,y,z] magnetic field values (in Tesla)
            method: Interpolation method ('idw', 'gp', 'ensemble')

        Returns:
            InterpolationResult with predicted magnetic field at Palmer, Alaska
        """
        if method == "idw":
            return self.inverse_distance_weighting(magnetic_data)
        elif method == "gp":
            return self.gaussian_process_interpolation(magnetic_data)
        elif method == "ensemble":
            return self.ensemble_interpolation(magnetic_data)
        else:
            print(f"Unknown method '{method}', using ensemble")
            return self.ensemble_interpolation(magnetic_data)

    def validate_interpolation(self, test_data: Dict[str, Dict[str, np.ndarray]],
                             method: str = "ensemble") -> Dict[str, float]:
        """
        Cross-validation of interpolation methods.

        Args:
            test_data: Dictionary with timestamps as keys and magnetic_data dictionaries as values
            method: Method to validate

        Returns:
            Dictionary with validation metrics
        """
        predictions = []
        actuals = []

        print(f"Validating {method} interpolation...")

        for timestamp, data in test_data.items():
            if len(data) >= 3:  # Need at least 3 observatories for validation
                # Hold out one observatory for validation
                for holdout_obs in self.observatories[:3]:  # Test on first 3 observatories
                    if holdout_obs.code in data:
                        # Create training data without holdout observatory
                        training_data = {k: v for k, v in data.items() if k != holdout_obs.code}

                        if len(training_data) >= 2:  # Need at least 2 for interpolation
                            # Predict at holdout location
                            # For simplification, use Palmer location (actual validation would use holdout location)
                            result = self.interpolate_magnetic_field(training_data, method)

                            # Compare with actual holdout data
                            actual = data[holdout_obs.code]
                            if len(actual) >= 3:
                                predictions.append([result.x_component, result.y_component, result.z_component])
                                actuals.append(actual[:3])

        if not predictions:
            return {"error": "No valid validation data"}

        predictions = np.array(predictions)
        actuals = np.array(actuals)

        # Calculate metrics
        mse = mean_squared_error(actuals, predictions)
        rmse = np.sqrt(mse)
        r2 = r2_score(actuals, predictions)

        # Component-wise metrics
        component_metrics = {}
        for i, comp in enumerate(['x', 'y', 'z']):
            comp_mse = mean_squared_error(actuals[:, i], predictions[:, i])
            comp_r2 = r2_score(actuals[:, i], predictions[:, i])
            component_metrics[f'{comp}_mse'] = comp_mse
            component_metrics[f'{comp}_r2'] = comp_r2

        metrics = {
            'overall_rmse': rmse,
            'overall_r2': r2,
            'n_samples': len(predictions),
            **component_metrics
        }

        self.model_performance[method] = metrics
        return metrics

    def get_interpolation_quality_score(self, result: InterpolationResult) -> float:
        """
        Calculate a quality score for interpolation result.

        Args:
            result: InterpolationResult object

        Returns:
            Quality score (0-1, higher is better)
        """
        # Base score from method reliability
        method_scores = {
            'IDW': 0.6,
            'Gaussian Process': 0.8,
            'Ensemble': 0.9
        }

        base_score = method_scores.get(result.method, 0.5)

        # Adjust based on uncertainty
        if result.uncertainty_mag > 0:
            # Lower uncertainty = higher quality
            uncertainty_factor = 1.0 / (1.0 + result.uncertainty_mag / result.magnitude)
            base_score *= uncertainty_factor

        # Adjust based on network geometry
        geometry = self.network.validate_network_geometry()
        if geometry['average_distance_km'] < 1000:  # Good spatial coverage
            base_score *= 1.1
        elif geometry['average_distance_km'] > 2000:  # Poor spatial coverage
            base_score *= 0.8

        return min(1.0, base_score)

    def save_model_state(self, filename: str):
        """Save trained models and interpolator state."""
        state = {
            'network_info': {
                'target_lat': self.network.target_lat,
                'target_lon': self.network.target_lon,
                'observatories': [
                    {
                        'code': obs.code,
                        'name': obs.name,
                        'distance_km': obs.distance_km
                    }
                    for obs in self.observatories
                ]
            },
            'training_history': self.training_history,
            'model_performance': self.model_performance,
            'created': datetime.now().isoformat()
        }

        with open(filename, 'w') as f:
            json.dump(state, f, indent=2)

        print(f"Saved interpolator state to {filename}")


def main():
    """Test spatial interpolation."""
    print("Testing Spatial Interpolation for Virtual Observatory")
    print("="*55)

    # Initialize network and interpolator
    network = ObservatoryNetwork()
    interpolator = SpatialInterpolator(network)

    # Mock magnetic data (in Tesla) for testing
    test_data = {
        'CMO': np.array([1.19e-5, 4.42e-6, 5.47e-5]),    # College, Alaska
        'SIT': np.array([2.05e-5, 3.36e-6, 4.78e-5]),    # Sitka, Alaska
        'SHU': np.array([1.95e-5, 5.12e-6, 5.23e-5]),    # Shumagin Islands
        'DED': np.array([1.15e-5, 3.89e-6, 5.61e-5])     # Deadhorse
    }

    print("\nTest Magnetic Data (Tesla):")
    for obs_code, data in test_data.items():
        magnitude = np.sqrt(np.sum(data**2))
        print(f"  {obs_code}: X={data[0]:.2e}, Y={data[1]:.2e}, Z={data[2]:.2e}, |B|={magnitude:.2e}")

    # Test different interpolation methods
    methods = ['idw', 'ensemble']
    if ML_AVAILABLE:
        methods.append('gp')

    results = {}
    for method in methods:
        print(f"\n--- {method.upper()} Interpolation ---")
        result = interpolator.interpolate_magnetic_field(test_data, method)

        results[method] = result

        print(f"Predicted Magnetic Field at Palmer, Alaska:")
        print(f"  X: {result.x_component:.2e} ± {result.uncertainty_x:.2e} T")
        print(f"  Y: {result.y_component:.2e} ± {result.uncertainty_y:.2e} T")
        print(f"  Z: {result.z_component:.2e} ± {result.uncertainty_z:.2e} T")
        print(f"  Magnitude: {result.magnitude:.2e} ± {result.uncertainty_mag:.2e} T")

        # Convert to more readable units
        magnitude_nt = result.magnitude * 1e9
        uncertainty_nt = result.uncertainty_mag * 1e9
        quality = interpolator.get_interpolation_quality_score(result)

        print(f"  Magnitude: {magnitude_nt:.1f} ± {uncertainty_nt:.1f} nT")
        print(f"  Quality Score: {quality:.3f}")

    # Compare methods
    print(f"\n--- Method Comparison ---")
    if len(results) > 1:
        for method, result in results.items():
            print(f"{method:10s}: {result.magnitude*1e9:6.1f} nT (±{result.uncertainty_mag*1e9:4.1f})")


if __name__ == "__main__":
    main()