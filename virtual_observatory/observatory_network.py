#!/usr/bin/env python3
"""
Observatory Network Manager

Manages the network of USGS geomagnetic observatories for virtual observatory creation.
Identifies the 4 nearest observatories to Palmer, Alaska and provides data access.
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Observatory:
    """Represents a USGS geomagnetic observatory."""
    code: str
    name: str
    latitude: float
    longitude: float
    elevation: float = 0.0
    distance_km: float = 0.0
    established: str = ""
    description: str = ""


class ObservatoryNetwork:
    """Manages USGS geomagnetic observatory network for virtual observatory."""

    def __init__(self, target_lat: float = 61.5994, target_lon: float = -149.115):
        """Initialize with target location (Palmer, Alaska)."""
        self.target_lat = target_lat
        self.target_lon = target_lon
        self.observatories = self._initialize_observatories()
        self.nearest_four = self._find_nearest_four()

    def _initialize_observatories(self) -> Dict[str, Observatory]:
        """Initialize all USGS geomagnetic observatories with coordinates."""
        observatories = {}

        # USGS Geomagnetic Observatories (14 total in US/Territories)
        # Focus on those most relevant to Alaska/Pacific region

        # Alaska Observatories
        observatories['CMO'] = Observatory(
            code='CMO',
            name='College',
            latitude=64.8742,   # Fairbanks area
            longitude=-147.8597,
            elevation=200,
            established='1948',
            description='University of Alaska Fairbanks campus'
        )

        observatories['SIT'] = Observatory(
            code='SIT',
            name='Sitka',
            latitude=57.0576,
            longitude=-135.3273,
            elevation=24,
            established='1901',
            description='Southeast Alaska, partnership with BLM'
        )

        observatories['BRW'] = Observatory(
            code='BRW',
            name='Barrow',
            latitude=71.323,
            longitude=-156.609,
            elevation=8,
            established='1949',
            description='Northernmost USGS observatory, within auroral oval'
        )

        observatories['DED'] = Observatory(
            code='DED',
            name='Deadhorse',
            latitude=70.2007,
            longitude=-148.4598,
            elevation=5,
            established='2010',
            description='USGS-Schlumberger partnership, North Slope'
        )

        # Continental US Observatories (for additional spatial coverage)
        observatories['BOU'] = Observatory(
            code='BOU',
            name='Boulder',
            latitude=40.1378,
            longitude=-105.2372,
            elevation=1682,
            established='1963',
            description='Colorado, primary USGS headquarters observatory'
        )

        observatories['FRD'] = Observatory(
            code='FRD',
            name='Fredericksburg',
            latitude=38.2047,
            longitude=-77.3729,
            elevation=69,
            established='1956',
            description='Virginia, eastern US reference'
        )

        observatories['TUC'] = Observatory(
            code='TUC',
            name='Tucson',
            latitude=32.1697,
            longitude=-110.7267,
            elevation=946,
            established='1963',
            description='Arizona, southwestern US'
        )

        observatories['HON'] = Observatory(
            code='HON',
            name='Honolulu',
            latitude=21.3158,
            longitude=-158.0058,
            elevation=4,
            established='1902',
            description='Hawaii, Pacific observatory'
        )

        observatories['SJG'] = Observatory(
            code='SJG',
            name='San Juan',
            latitude=18.1139,
            longitude=-66.1503,
            elevation=424,
            established='1926',
            description='Puerto Rico, Caribbean observatory'
        )

        observatories['GUA'] = Observatory(
            code='GUA',
            name='Guam',
            latitude=13.5892,
            longitude=144.8689,
            elevation=140,
            established='1957',
            description='Western Pacific observatory'
        )

        observatories['FRN'] = Observatory(
            code='FRN',
            name='Fresno',
            latitude=37.0911,
            longitude=-119.7198,
            elevation=331,
            established='1982',
            description='California, San Joaquin Valley'
        )

        observatories['NEW'] = Observatory(
            code='NEW',
            name='Newport',
            latitude=48.2647,
            longitude=-117.1214,
            elevation=770,
            established='1969',
            description='Washington State, Pacific Northwest'
        )

        observatories['BSL'] = Observatory(
            code='BSL',
            name='Stennis',
            latitude=30.3497,
            longitude=-89.6244,
            elevation=8,
            established='1982',
            description='Mississippi, Gulf Coast'
        )

        observatories['SHU'] = Observatory(
            code='SHU',
            name='Shumagin',
            latitude=55.3481,
            longitude=-160.4564,
            elevation=80,
            established='1902',
            description='Aleutian Islands, Alaska'
        )

        return observatories

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great circle distance between two points on Earth using Haversine formula."""
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in kilometers
        earth_radius_km = 6371.0

        return earth_radius_km * c

    def _find_nearest_four(self) -> List[Observatory]:
        """Find the 4 nearest observatories to Palmer, Alaska."""
        # Calculate distances for all observatories
        for obs in self.observatories.values():
            obs.distance_km = self.haversine_distance(
                self.target_lat, self.target_lon,
                obs.latitude, obs.longitude
            )

        # Sort by distance and take the 4 nearest
        sorted_obs = sorted(self.observatories.values(), key=lambda x: x.distance_km)
        return sorted_obs[:4]

    def get_nearest_observatories(self) -> List[Observatory]:
        """Get the 4 nearest observatories to the target location."""
        return self.nearest_four

    def get_observatory_by_code(self, code: str) -> Optional[Observatory]:
        """Get observatory by code."""
        return self.observatories.get(code)

    def get_spatial_weights(self) -> np.ndarray:
        """Calculate inverse distance weights for spatial interpolation."""
        distances = np.array([obs.distance_km for obs in self.nearest_four])

        # Inverse distance weighting (avoid division by zero for exact matches)
        weights = 1.0 / (distances + 1e-6)  # Add small epsilon

        # Normalize weights to sum to 1
        weights = weights / np.sum(weights)

        return weights

    def get_coordinate_matrix(self) -> np.ndarray:
        """Get coordinate matrix for the 4 nearest observatories."""
        coords = np.array([
            [obs.latitude, obs.longitude, obs.elevation]
            for obs in self.nearest_four
        ])
        return coords

    def print_network_summary(self):
        """Print summary of observatory network and nearest stations."""
        print("\n" + "="*80)
        print("VIRTUAL OBSERVATORY NETWORK ANALYSIS")
        print("="*80)
        print(f"Target Location: Palmer, Alaska")
        print(f"Coordinates: {self.target_lat:.4f}°N, {self.target_lon:.4f}°W")

        print(f"\n4 Nearest USGS Geomagnetic Observatories:")
        print("-" * 60)

        for i, obs in enumerate(self.nearest_four, 1):
            direction = self._get_cardinal_direction(obs.latitude - self.target_lat,
                                                   obs.longitude - self.target_lon)
            print(f"{i}. {obs.code} - {obs.name}")
            print(f"   Location: {obs.latitude:.4f}°N, {obs.longitude:.4f}°W")
            print(f"   Distance: {obs.distance_km:.1f} km ({direction})")
            print(f"   Established: {obs.established}")
            print(f"   Description: {obs.description}")
            print()

        # Spatial coverage analysis
        weights = self.get_spatial_weights()
        print("Spatial Interpolation Weights:")
        print("-" * 30)
        for obs, weight in zip(self.nearest_four, weights):
            print(f"  {obs.code}: {weight:.3f} ({weight*100:.1f}%)")

        print("\nNetwork Coverage Analysis:")
        print("-" * 25)
        lats = [obs.latitude for obs in self.nearest_four]
        lons = [obs.longitude for obs in self.nearest_four]
        print(f"  Latitude span: {max(lats) - min(lats):.1f}° ({min(lats):.1f}° to {max(lats):.1f}°)")
        print(f"  Longitude span: {max(lons) - min(lons):.1f}° ({min(lons):.1f}° to {max(lons):.1f}°)")
        print(f"  Average distance: {np.mean([obs.distance_km for obs in self.nearest_four]):.1f} km")

        print("="*80)

    def _get_cardinal_direction(self, dlat: float, dlon: float) -> str:
        """Get cardinal direction based on lat/lon differences."""
        if abs(dlat) > abs(dlon):
            return "North" if dlat > 0 else "South"
        else:
            return "East" if dlon > 0 else "West"

    def validate_network_geometry(self) -> Dict[str, float]:
        """Validate the geometric properties of the observatory network."""
        coords = self.get_coordinate_matrix()

        # Calculate network properties
        centroid_lat = np.mean(coords[:, 0])
        centroid_lon = np.mean(coords[:, 1])

        # Distance from target to network centroid
        centroid_distance = self.haversine_distance(
            self.target_lat, self.target_lon,
            centroid_lat, centroid_lon
        )

        # Network spread (standard deviation of distances from centroid)
        distances_to_centroid = [
            self.haversine_distance(centroid_lat, centroid_lon, coord[0], coord[1])
            for coord in coords
        ]
        network_spread = np.std(distances_to_centroid)

        # Aspect ratio (lat span / lon span)
        lat_span = np.max(coords[:, 0]) - np.min(coords[:, 0])
        lon_span = np.max(coords[:, 1]) - np.min(coords[:, 1])
        aspect_ratio = lat_span / (lon_span + 1e-6)  # Avoid division by zero

        return {
            'centroid_distance_km': centroid_distance,
            'network_spread_km': network_spread,
            'aspect_ratio': aspect_ratio,
            'lat_span_degrees': lat_span,
            'lon_span_degrees': lon_span,
            'average_distance_km': np.mean([obs.distance_km for obs in self.nearest_four])
        }


def main():
    """Test the observatory network."""
    print("Observatory Network Analysis for Virtual Observatory")
    print("="*55)

    # Create network
    network = ObservatoryNetwork()

    # Print network summary
    network.print_network_summary()

    # Validate geometry
    geometry = network.validate_network_geometry()
    print("\nNetwork Geometry Validation:")
    print("-" * 30)
    for key, value in geometry.items():
        print(f"  {key}: {value:.2f}")


if __name__ == "__main__":
    main()