# Virtual Geomagnetic Observatory System
## Complete User Guide and Documentation

### 📖 Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Installation & Setup](#installation--setup)
4. [Quick Start Guide](#quick-start-guide)
5. [Virtual Observatory Usage](#virtual-observatory-usage)
6. [Plotting and Visualization](#plotting-and-visualization)
7. [Creating New Synthetic Observatories](#creating-new-synthetic-observatories)
8. [Configuration Management](#configuration-management)
9. [Data Analysis Features](#data-analysis-features)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Usage](#advanced-usage)
12. [API Reference](#api-reference)

---

## Overview

The Virtual Geomagnetic Observatory System creates synthetic magnetic field observatories using AI/ML spatial interpolation from existing USGS geomagnetic stations. This system can predict magnetic field values at any location by analyzing data from the nearest reference observatories.

### 🎯 Key Features

- **ML-based spatial interpolation** using multiple algorithms (IDW, Gaussian Process, Ensemble)
- **Automatic observatory network selection** (4 nearest USGS stations)
- **Real-time magnetic field prediction** with uncertainty quantification
- **Local sensor validation** and coordinate transformation
- **Comprehensive visualization** (time series, polar plots, network maps)
- **NIST SP 330 SI unit compliance** (Tesla)
- **Configurable parameters** for different locations and requirements

---

## System Architecture

```
Virtual Observatory System
├── Observatory Network (observatory_network.py)
│   ├── USGS station database (14 observatories)
│   ├── Haversine distance calculations
│   ├── Automatic nearest-4 selection
│   └── Spatial weight calculations
│
├── Spatial Interpolation (spatial_interpolation.py)
│   ├── Inverse Distance Weighting (IDW)
│   ├── Gaussian Process Regression
│   ├── Ensemble methods
│   └── Uncertainty quantification
│
├── Virtual Station Predictor (virtual_station_predictor.py)
│   ├── Data collection & processing
│   ├── Real-time predictions
│   ├── Local sensor validation
│   └── Quality assessment
│
├── Plotting & Visualization
│   ├── Comprehensive comparison plots
│   ├── Polar magnitude analysis
│   └── Network geometry visualization
│
└── Configuration Management
    ├── Location parameters
    ├── Interpolation settings
    └── Validation thresholds
```

---

## Installation & Setup

### Prerequisites

- Python 3.8+ with virtual environment
- Required packages: numpy, pandas, matplotlib, scikit-learn, sqlite3

### Installation

```bash
# Clone or ensure you have the weatherstation project
cd /path/to/weatherstation

# Install required packages
./venv/bin/pip install scikit-learn pandas matplotlib numpy

# Verify installation
./venv/bin/python -c "import sklearn; print('scikit-learn version:', sklearn.__version__)"
```

### File Structure

Ensure these files exist in your project:
```
weatherstation/
├── virtual_observatory/
│   ├── __init__.py
│   ├── observatory_network.py
│   ├── spatial_interpolation.py
│   └── virtual_station_predictor.py
├── config/
│   └── virtual_observatory_config.json
├── virtual_observatory_plotter.py
├── virtual_observatory_polar_plotter.py
├── demo_virtual_observatory.py
└── weather_station_calibration.json (if using local sensor)
```

---

## Quick Start Guide

### 1. Basic Virtual Observatory Demo

```bash
# Run the demonstration script
./venv/bin/python demo_virtual_observatory.py
```

This will show:
- Observatory network analysis for Palmer, Alaska
- ML interpolation results using multiple methods
- Network geometry validation
- Geophysical context and technical details

### 2. Generate Observatory Data

```bash
# Test the observatory network
./venv/bin/python -c "
from virtual_observatory.observatory_network import ObservatoryNetwork
network = ObservatoryNetwork()  # Default: Palmer, Alaska
network.print_network_summary()
"
```

### 3. Single Prediction

```bash
# Generate a single virtual observatory reading
./venv/bin/python -c "
from virtual_observatory.virtual_station_predictor import VirtualObservatoryPredictor
import numpy as np

predictor = VirtualObservatoryPredictor()

# Simulate USGS data (realistic Palmer values)
usgs_data = {
    'CMO': np.array([55.7e-6, 2.1e-6, 54.2e-6]),
    'SIT': np.array([54.2e-6, 1.8e-6, 53.1e-6]),
    'SHU': np.array([53.8e-6, 2.3e-6, 52.9e-6]),
    'DED': np.array([56.1e-6, 1.9e-6, 54.8e-6])
}

result = predictor.interpolator.inverse_distance_weighting(usgs_data)
print(f'Virtual Observatory Reading: {result.magnitude*1e6:.1f} μT')
"
```

---

## Virtual Observatory Usage

### Creating a Virtual Observatory

#### For Palmer, Alaska (Default)

```python
from virtual_observatory.virtual_station_predictor import VirtualObservatoryPredictor

# Use default Palmer, Alaska configuration
predictor = VirtualObservatoryPredictor()

# View network configuration
predictor.network.print_network_summary()
```

#### For Custom Location

```python
from virtual_observatory.observatory_network import ObservatoryNetwork
from virtual_observatory.spatial_interpolation import SpatialInterpolator

# Create network for custom location
latitude = 64.8378   # Fairbanks, Alaska
longitude = -147.7164

network = ObservatoryNetwork(target_lat=latitude, target_lon=longitude)
interpolator = SpatialInterpolator(network)

# View nearest observatories
network.print_network_summary()
```

### Interpolation Methods

#### 1. Inverse Distance Weighting (IDW)

```python
# Most reliable method for geomagnetic data
result = interpolator.inverse_distance_weighting(usgs_data)
quality = interpolator.get_interpolation_quality_score(result)

print(f"IDW Result: {result.magnitude*1e6:.1f} μT (Quality: {quality:.3f})")
```

#### 2. Gaussian Process Regression

```python
# Advanced ML method with uncertainty quantification
result = interpolator.gaussian_process_interpolation(usgs_data)
quality = interpolator.get_interpolation_quality_score(result)

print(f"GP Result: {result.magnitude*1e6:.1f} μT (Uncertainty: ±{result.uncertainty_mag*1e6:.1f} μT)")
```

#### 3. Ensemble Method

```python
# Combines IDW and GP for robust predictions
result = interpolator.ensemble_interpolation(usgs_data)
quality = interpolator.get_interpolation_quality_score(result)

print(f"Ensemble Result: {result.magnitude*1e6:.1f} μT")
```

---

## Plotting and Visualization

### 1. Comprehensive Comparison Plots

```bash
# Basic comparison (virtual observatory vs local sensor vs USGS data)
./venv/bin/python virtual_observatory_plotter.py --hours 24

# Custom time range and output
./venv/bin/python virtual_observatory_plotter.py --hours 6 --output my_analysis.png

# Extended analysis
./venv/bin/python virtual_observatory_plotter.py --hours 72 --output 3day_analysis.png
```

**Features:**
- Magnetic field magnitude comparison
- X, Y, Z component analysis
- Virtual observatory uncertainty bands
- Quality score tracking
- Observatory network geometry map
- Statistical comparison metrics

### 2. Polar Magnitude Analysis

```bash
# Polar coordinate visualization
./venv/bin/python virtual_observatory_polar_plotter.py --hours 12

# Short-term high resolution
./venv/bin/python virtual_observatory_polar_plotter.py --hours 3 --output polar_detail.png
```

**Features:**
- Horizontal magnetic field in polar coordinates
- 3D magnetic inclination vs magnitude
- Time series of azimuth and inclination
- Geomagnetic coordinate validation
- Statistical comparison charts

### 3. Batch Plot Generation

```bash
# Generate multiple comparison plots
./examples_virtual_observatory_plots.sh

# Generate multiple polar plots
./examples_polar_plots.sh
```

---

## Creating New Synthetic Observatories

### Step 1: Choose Target Location

Select coordinates for your new virtual observatory:

```python
# Example locations
locations = {
    "Anchorage, AK": (61.2181, -149.9003),
    "Fairbanks, AK": (64.8378, -147.7164),
    "Juneau, AK": (58.3019, -134.4197),
    "Nome, AK": (64.5011, -165.4064),
    "Barrow, AK": (71.2906, -156.7886),
    # Any worldwide location
    "Reykjavik, Iceland": (64.1466, -21.9426),
    "Tromsø, Norway": (69.6492, 18.9553)
}

target_lat, target_lon = locations["Fairbanks, AK"]
```

### Step 2: Create Configuration File

Create a custom configuration file for your location:

```python
import json
from datetime import datetime

# Configuration template
config = {
    "version": "1.0",
    "created": datetime.now().isoformat(),
    "description": f"Virtual Geomagnetic Observatory Configuration for Fairbanks, Alaska",

    "target_location": {
        "latitude": 64.8378,
        "longitude": -147.7164,
        "elevation": 133,  # meters
        "name": "Fairbanks, Alaska",
        "magnetic_declination": -15.8,  # degrees (look up for your location)
        "comments": "University of Alaska Fairbanks area"
    },

    "interpolation": {
        "method": "idw",  # or "gp" or "ensemble"
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
        "local_sensor_available": False,  # Set to True if you have local data
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
        "preferred_observatories": ["CMO", "SIT", "BRW", "DED"],  # Adjust for your region
        "fallback_observatories": ["BOU", "NEW", "FRD"],
        "max_distance_km": 2000,
        "weight_by_distance": True
    }
}

# Save configuration
with open(f'config/virtual_observatory_{config["target_location"]["name"].lower().replace(" ", "_").replace(",", "")}_config.json', 'w') as f:
    json.dump(config, f, indent=2)
```

### Step 3: Initialize Virtual Observatory

```python
from virtual_observatory.virtual_station_predictor import VirtualObservatoryPredictor

# Create virtual observatory for new location
predictor = VirtualObservatoryPredictor(
    config_file='config/virtual_observatory_fairbanks_alaska_config.json'
)

# Analyze the observatory network
predictor.network.print_network_summary()

# Validate network geometry
geometry = predictor.network.validate_network_geometry()
print("Network Geometry:")
for key, value in geometry.items():
    print(f"  {key}: {value:.2f}")
```

### Step 4: Generate Predictions

```python
import numpy as np

# You would normally collect real USGS data here
# For demonstration, we'll simulate realistic values for your region

# Look up typical magnetic field values for your location at:
# https://www.ngdc.noaa.gov/geomag/calculators/magcalc.shtml

# Example for Fairbanks area (adjust for your location)
simulated_usgs_data = {
    'CMO': np.array([56.2e-6, 1.8e-6, 55.1e-6]),  # Nearest station
    'BRW': np.array([58.1e-6, 0.9e-6, 57.2e-6]),  # Barrow
    'SIT': np.array([54.8e-6, 2.1e-6, 53.9e-6]),  # Sitka
    'DED': np.array([57.3e-6, 1.5e-6, 56.0e-6])   # Deadhorse
}

# Generate prediction
result = predictor.interpolator.inverse_distance_weighting(simulated_usgs_data)
quality = predictor.interpolator.get_interpolation_quality_score(result)

print(f"\nFairbanks Virtual Observatory Prediction:")
print(f"  Magnitude: {result.magnitude*1e6:.1f} μT")
print(f"  Components: X={result.x_component*1e6:.1f}, Y={result.y_component*1e6:.1f}, Z={result.z_component*1e6:.1f} μT")
print(f"  Quality Score: {quality:.3f}")
print(f"  Uncertainty: ±{result.uncertainty_mag*1e6:.1f} μT")
```

### Step 5: Validation and Testing

```python
# Test different interpolation methods
methods = ['IDW', 'Gaussian Process', 'Ensemble']
results = []

# IDW
result_idw = predictor.interpolator.inverse_distance_weighting(simulated_usgs_data)
quality_idw = predictor.interpolator.get_interpolation_quality_score(result_idw)
results.append(('IDW', result_idw, quality_idw))

# Gaussian Process (with warnings suppressed)
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    result_gp = predictor.interpolator.gaussian_process_interpolation(simulated_usgs_data)
    quality_gp = predictor.interpolator.get_interpolation_quality_score(result_gp)
    results.append(('GP', result_gp, quality_gp))

# Ensemble
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    result_ensemble = predictor.interpolator.ensemble_interpolation(simulated_usgs_data)
    quality_ensemble = predictor.interpolator.get_interpolation_quality_score(result_ensemble)
    results.append(('Ensemble', result_ensemble, quality_ensemble))

# Compare methods
print(f"\nMethod Comparison for Fairbanks:")
print("-" * 50)
for method, result, quality in results:
    print(f"{method:12s}: {result.magnitude*1e6:5.1f} μT (Quality: {quality:.3f})")

# Choose best method
best_method, best_result, best_quality = max(results, key=lambda x: x[2])
print(f"\nBest Method: {best_method} (Quality: {best_quality:.3f})")
```

---

## Configuration Management

### Configuration File Structure

```json
{
  "version": "1.0",
  "target_location": {
    "latitude": 61.5994,
    "longitude": -149.115,
    "elevation": 70,
    "name": "Palmer, Alaska",
    "magnetic_declination": -17.5
  },
  "interpolation": {
    "method": "idw",
    "idw_power": 2.0,
    "uncertainty_threshold": 0.1
  },
  "validation": {
    "alert_threshold_percent": 20,
    "enable_alerts": true
  },
  "observatory_network": {
    "max_distance_km": 2000,
    "weight_by_distance": true
  }
}
```

### Key Parameters

#### Target Location
- **latitude/longitude**: Target coordinates in decimal degrees
- **elevation**: Height above sea level in meters
- **magnetic_declination**: Local magnetic declination in degrees

#### Interpolation Settings
- **method**: "idw", "gp", or "ensemble"
- **idw_power**: Power parameter for inverse distance weighting (typically 2.0)
- **uncertainty_threshold**: Quality threshold for accepting predictions

#### Validation Settings
- **alert_threshold_percent**: Acceptable difference between virtual and local sensor
- **validation_window_minutes**: Time window for local sensor comparison

---

## Data Analysis Features

### Quality Assessment

```python
# Assess prediction quality
quality_metrics = {
    'quality_score': quality,
    'uncertainty': result.uncertainty_mag * 1e6,
    'method': result.method,
    'network_geometry': geometry['average_distance_km']
}

print("Quality Assessment:")
for metric, value in quality_metrics.items():
    print(f"  {metric}: {value}")
```

### Statistical Analysis

```python
# Generate time series for statistical analysis
time_series = []
for i in range(24):  # 24 hours of hourly predictions
    # Simulate time-varying data
    time_factor = 0.01 * np.sin(2 * np.pi * i / 24)
    varied_data = {
        code: base_field * (1 + time_factor + np.random.normal(0, 0.001))
        for code, base_field in simulated_usgs_data.items()
    }

    result = predictor.interpolator.inverse_distance_weighting(varied_data)
    time_series.append({
        'hour': i,
        'magnitude': result.magnitude * 1e6,
        'x': result.x_component * 1e6,
        'y': result.y_component * 1e6,
        'z': result.z_component * 1e6
    })

# Calculate statistics
import pandas as pd
df = pd.DataFrame(time_series)

print("24-Hour Statistics:")
print(f"  Mean magnitude: {df['magnitude'].mean():.1f} ± {df['magnitude'].std():.1f} μT")
print(f"  Range: {df['magnitude'].min():.1f} - {df['magnitude'].max():.1f} μT")
print(f"  Daily variation: {df['magnitude'].max() - df['magnitude'].min():.1f} μT")
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Error: No module named 'sklearn'
./venv/bin/pip install scikit-learn

# Error: No module named 'virtual_observatory'
# Ensure you're running from the correct directory
cd /path/to/weatherstation
```

#### 2. Configuration File Not Found
```python
# Check file path
import os
config_path = 'config/virtual_observatory_config.json'
if not os.path.exists(config_path):
    print(f"Config file not found: {config_path}")
    print(f"Current directory: {os.getcwd()}")
```

#### 3. Unrealistic Magnetic Field Values
```python
# Check input data ranges (should be ~50-80 μT for most locations)
for code, data in usgs_data.items():
    magnitude = np.linalg.norm(data) * 1e6
    print(f"{code}: {magnitude:.1f} μT")
    if magnitude < 20 or magnitude > 100:
        print(f"  WARNING: {code} has unusual magnitude")
```

#### 4. Poor Quality Scores
```python
# Check network geometry
geometry = network.validate_network_geometry()
if geometry['average_distance_km'] > 1500:
    print("WARNING: Observatory network may be too sparse")
    print("Consider locations closer to existing USGS stations")
```

### Debugging Tips

#### Enable Verbose Output
```python
# Add debugging prints
print(f"Network observatories: {[obs.code for obs in network.nearest_four]}")
print(f"Spatial weights: {network.get_spatial_weights()}")
print(f"Input data magnitudes: {[np.linalg.norm(data)*1e6 for data in usgs_data.values()]}")
```

#### Validate Input Data
```python
def validate_usgs_data(usgs_data):
    """Validate USGS input data for reasonableness."""
    for code, data in usgs_data.items():
        if len(data) != 3:
            print(f"ERROR: {code} data must have 3 components")
            return False

        magnitude = np.linalg.norm(data) * 1e6
        if magnitude < 20 or magnitude > 100:
            print(f"WARNING: {code} magnitude ({magnitude:.1f} μT) outside typical range")

        # Check for NaN or infinite values
        if not np.all(np.isfinite(data)):
            print(f"ERROR: {code} contains NaN or infinite values")
            return False

    return True

# Use before interpolation
if validate_usgs_data(usgs_data):
    result = interpolator.inverse_distance_weighting(usgs_data)
```

---

## Advanced Usage

### Custom Interpolation Parameters

```python
# Create interpolator with custom parameters
from virtual_observatory.spatial_interpolation import SpatialInterpolator

class CustomInterpolator(SpatialInterpolator):
    def custom_idw(self, magnetic_data, power=1.5):
        """IDW with custom power parameter."""
        return self.inverse_distance_weighting(magnetic_data, power=power)

# Use custom interpolator
interpolator = CustomInterpolator(network)
result = interpolator.custom_idw(usgs_data, power=1.5)
```

### Batch Processing

```python
# Process multiple locations
locations = [
    ("Anchorage", 61.2181, -149.9003),
    ("Fairbanks", 64.8378, -147.7164),
    ("Juneau", 58.3019, -134.4197)
]

results = {}
for name, lat, lon in locations:
    network = ObservatoryNetwork(target_lat=lat, target_lon=lon)
    interpolator = SpatialInterpolator(network)

    # Use same USGS data for comparison
    result = interpolator.inverse_distance_weighting(usgs_data)

    results[name] = {
        'magnitude': result.magnitude * 1e6,
        'nearest_obs': [obs.code for obs in network.nearest_four],
        'avg_distance': np.mean([obs.distance_km for obs in network.nearest_four])
    }

# Compare results
for name, data in results.items():
    print(f"{name}: {data['magnitude']:.1f} μT, nearest: {data['nearest_obs']}, avg dist: {data['avg_distance']:.0f} km")
```

### Integration with Real USGS Data

```python
# Example framework for fetching real USGS data
def fetch_usgs_data(observatory_codes, time_range_hours=1):
    """
    Fetch real USGS data for specified observatories.
    This is a template - implement actual USGS API calls.
    """
    # Implementation would use USGS web services
    # https://www.usgs.gov/natural-hazards/geomagnetism/science/web-services

    # Return format should match simulation
    return {
        code: np.array([x, y, z])  # In Tesla
        for code in observatory_codes
    }

# Use with virtual observatory
observatory_codes = [obs.code for obs in network.nearest_four]
real_usgs_data = fetch_usgs_data(observatory_codes)
result = interpolator.inverse_distance_weighting(real_usgs_data)
```

---

## API Reference

### ObservatoryNetwork Class

```python
from virtual_observatory.observatory_network import ObservatoryNetwork

network = ObservatoryNetwork(target_lat=61.5994, target_lon=-149.115)
```

**Methods:**
- `get_nearest_observatories()` → List[Observatory]
- `get_spatial_weights()` → np.ndarray
- `haversine_distance(lat1, lon1, lat2, lon2)` → float
- `print_network_summary()` → None
- `validate_network_geometry()` → Dict[str, float]

### SpatialInterpolator Class

```python
from virtual_observatory.spatial_interpolation import SpatialInterpolator

interpolator = SpatialInterpolator(network)
```

**Methods:**
- `inverse_distance_weighting(magnetic_data, power=2.0)` → InterpolationResult
- `gaussian_process_interpolation(magnetic_data)` → InterpolationResult
- `ensemble_interpolation(magnetic_data)` → InterpolationResult
- `get_interpolation_quality_score(result)` → float

### VirtualObservatoryPredictor Class

```python
from virtual_observatory.virtual_station_predictor import VirtualObservatoryPredictor

predictor = VirtualObservatoryPredictor(db_path="weather_data.db", config_file="config.json")
```

**Methods:**
- `generate_virtual_reading()` → InterpolationResult
- `validate_against_local_sensor(result)` → Dict
- `continuous_monitoring(duration_hours)` → None

### InterpolationResult DataClass

```python
@dataclass
class InterpolationResult:
    x_component: float        # Tesla
    y_component: float        # Tesla
    z_component: float        # Tesla
    magnitude: float          # Tesla
    uncertainty_x: float      # Tesla
    uncertainty_y: float      # Tesla
    uncertainty_z: float      # Tesla
    uncertainty_mag: float    # Tesla
    confidence_level: float   # 0-1
    method: str              # "IDW", "GP", "Ensemble"
    timestamp: datetime
```

---

## Summary

This virtual observatory system provides a complete framework for creating synthetic geomagnetic observatories anywhere in the world using machine learning spatial interpolation. The system is designed to be:

- **Flexible**: Easily configurable for any location
- **Accurate**: Uses proven interpolation methods with uncertainty quantification
- **Comprehensive**: Includes visualization, validation, and quality assessment
- **Extensible**: Modular design allows for custom modifications
- **Well-documented**: Complete API reference and examples

For additional support or questions, refer to the troubleshooting section or examine the example scripts provided.