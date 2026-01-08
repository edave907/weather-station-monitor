#!/bin/bash
"""
Virtual Observatory Plotting Examples
Palmer, Alaska Virtual Geomagnetic Observatory

Demonstrates various plotting scenarios comparing:
- Palmer Virtual Observatory (ML interpolation)
- 4 USGS reference observatories
- Local magnetic flux sensor data
"""

echo "🌍 Virtual Observatory Plotting Examples"
echo "========================================"
echo ""

# Example 1: Recent 6-hour comparison
echo "📊 Example 1: Recent 6-hour comparison"
echo "Generating 6-hour comparison plot..."
./venv/bin/python virtual_observatory_plotter.py --hours 6 --output virtual_obs_6h.png

echo ""

# Example 2: Full day comparison
echo "📊 Example 2: Full day (24-hour) comparison"
echo "Generating 24-hour comparison plot..."
./venv/bin/python virtual_observatory_plotter.py --hours 24 --output virtual_obs_24h.png

echo ""

# Example 3: Extended 3-day comparison
echo "📊 Example 3: Extended 3-day comparison"
echo "Generating 3-day comparison plot..."
./venv/bin/python virtual_observatory_plotter.py --hours 72 --output virtual_obs_3day.png

echo ""

# Example 4: Short-term 1-hour high resolution
echo "📊 Example 4: Short-term 1-hour high resolution"
echo "Generating 1-hour high-resolution comparison plot..."
./venv/bin/python virtual_observatory_plotter.py --hours 1 --output virtual_obs_1h.png

echo ""

echo "✅ All plotting examples completed!"
echo ""
echo "Generated files:"
echo "  - virtual_obs_6h.png     (6-hour comparison)"
echo "  - virtual_obs_24h.png    (24-hour comparison)"
echo "  - virtual_obs_3day.png   (3-day comparison)"
echo "  - virtual_obs_1h.png     (1-hour high-res)"
echo ""
echo "📈 Features in each plot:"
echo "  • Magnetic field magnitude comparison"
echo "  • X, Y, Z component analysis"
echo "  • Virtual observatory uncertainty bands"
echo "  • Quality score tracking"
echo "  • Observatory network geometry map"
echo "  • Statistical comparison metrics"
echo ""
echo "🧮 Analysis includes:"
echo "  • Mean field strengths and variations"
echo "  • Correlation between virtual and local sensor"
echo "  • USGS observatory weights and contributions"
echo "  • Geomagnetic activity patterns"
echo "  • Network coverage and quality assessment"