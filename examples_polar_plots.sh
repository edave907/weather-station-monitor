#!/bin/bash
"""
Polar Magnitude Plotting Examples
Palmer, Alaska Virtual Geomagnetic Observatory

Creates polar coordinate visualizations comparing:
- Local magnetic flux sensor (coordinate corrected)
- Virtual observatory predictions (ML interpolation)
- Magnetic field direction and magnitude analysis
"""

echo "🧭 Virtual Observatory Polar Plotting Examples"
echo "=============================================="
echo ""

# Example 1: Recent 6-hour polar analysis
echo "📊 Example 1: Recent 6-hour polar analysis"
echo "Generating 6-hour polar magnitude plot..."
./venv/bin/python virtual_observatory_polar_plotter.py --hours 6 --output polar_6h.png

echo ""

# Example 2: Full day polar comparison
echo "📊 Example 2: Full day (24-hour) polar analysis"
echo "Generating 24-hour polar magnitude plot..."
./venv/bin/python virtual_observatory_polar_plotter.py --hours 24 --output polar_24h.png

echo ""

# Example 3: Short-term high resolution
echo "📊 Example 3: Short-term 3-hour high resolution"
echo "Generating 3-hour high-resolution polar plot..."
./venv/bin/python virtual_observatory_polar_plotter.py --hours 3 --output polar_3h.png

echo ""

# Example 4: Extended 2-day analysis
echo "📊 Example 4: Extended 2-day polar analysis"
echo "Generating 48-hour polar magnitude plot..."
./venv/bin/python virtual_observatory_polar_plotter.py --hours 48 --output polar_2day.png

echo ""

echo "✅ All polar plotting examples completed!"
echo ""
echo "Generated files:"
echo "  - polar_6h.png      (6-hour polar analysis)"
echo "  - polar_24h.png     (24-hour polar analysis)"
echo "  - polar_3h.png      (3-hour high-resolution)"
echo "  - polar_2day.png    (48-hour extended analysis)"
echo ""
echo "🧭 Features in each polar plot:"
echo "  • Horizontal magnetic field (XY plane) in polar coordinates"
echo "  • 3D magnetic inclination vs total magnitude"
echo "  • Time series of azimuth and inclination changes"
echo "  • Total magnitude comparison with uncertainty bands"
echo "  • Statistical comparison bar chart"
echo "  • Time-colored scatter plots showing field evolution"
echo ""
echo "📊 Analysis includes:"
echo "  • Magnetic declination and inclination measurements"
echo "  • Horizontal vs vertical field component analysis"
echo "  • Geomagnetic coordinate system validation"
echo "  • Palmer location magnetic field characteristics"
echo "  • Virtual observatory vs local sensor correlation"