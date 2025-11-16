#!/bin/bash
# USGS Magnetic Data Comparison Examples
#
# This script demonstrates how to import USGS reference data and compare it
# with local HMC5883L magnetic flux measurements.

set -e  # Exit on any error

echo "USGS Magnetic Data Comparison Examples"
echo "====================================="

# Activate virtual environment
if [ -f "./venv/bin/activate" ]; then
    source ./venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "Warning: Virtual environment not found, using system Python"
fi

echo
echo "1. Listing available USGS observatories..."
python usgs_magnetic_importer.py --list-observatories

echo
echo "2. Importing 24 hours of USGS reference data from College, Alaska (CMO) - closest to Palmer..."
python usgs_magnetic_importer.py --observatory CMO --hours 24

echo
echo "3. Showing USGS data summary..."
python usgs_magnetic_importer.py --summary --observatory CMO

echo
echo "4. Creating magnetic field comparison plots (if local data available)..."
if python -c "import sqlite3; conn = sqlite3.connect('weather_data.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM magnetic_flux_data'); result = cursor.fetchone()[0]; conn.close(); exit(0 if result > 0 else 1)" 2>/dev/null; then
    python magnetic_flux_comparison_plotter.py --observatory CMO --hours 12 --plots all
    echo "✓ Comparison plots created successfully"
else
    echo "ℹ No local magnetic flux data found. Run your weather station daemon first to collect data."
fi

echo
echo "5. Example: Import specific date range and create detailed comparison..."
echo "# Import data for a specific date range"
echo "python usgs_magnetic_importer.py --observatory CMO --start '2025-10-01' --end '2025-10-02'"
echo
echo "# Create correlation analysis for that period"
echo "python magnetic_flux_comparison_plotter.py --observatory CMO --start '2025-10-01 00:00' --end '2025-10-02 00:00' --plots correlation --save"

echo
echo "6. Example: Compare with different observatories based on location..."
echo "# For Alaska locations (Palmer area):"
echo "python usgs_magnetic_importer.py --observatory CMO --days 7  # College, Alaska (closest to Palmer)"
echo "python usgs_magnetic_importer.py --observatory SIT --days 7  # Sitka, Alaska"
echo
echo "# For Western US locations:"
echo "python usgs_magnetic_importer.py --observatory BOU --days 7  # Boulder, Colorado"
echo "python usgs_magnetic_importer.py --observatory TUC --days 7  # Tucson, Arizona"
echo
echo "# For Eastern US locations:"
echo "python usgs_magnetic_importer.py --observatory FRD --days 7  # Fredericksburg, Virginia"
echo
echo "# For Hawaii/Pacific:"
echo "python usgs_magnetic_importer.py --observatory HON --days 7  # Honolulu, Hawaii"

echo
echo "7. Advanced: Statistical analysis and validation..."
echo "# Compare local sensor calibration against USGS reference"
echo "python magnetic_flux_comparison_plotter.py --observatory BOU --hours 24 --plots all --save --output-dir validation_plots"
echo
echo "# The comparison will show:"
echo "  - Correlation coefficients between local and USGS data"
echo "  - RMS differences for X, Y, Z components"
echo "  - Statistical validation of sensor calibration"
echo "  - Identification of local magnetic anomalies"

echo
echo "✓ USGS comparison examples complete!"
echo
echo "Tips for optimal comparison:"
echo "- Choose the nearest USGS observatory to your location"
echo "- Import overlapping time periods for meaningful comparison"
echo "- Use correlation plots to validate sensor calibration"
echo "- Large differences may indicate local magnetic anomalies"
echo "- USGS data is in nanotesla, automatically converted to Tesla for NIST SP 330 compliance"

echo
echo "Observatory recommendations by region:"
echo "- Palmer, Alaska area: CMO (College/Fairbanks) - closest, ~240 miles"
echo "- Other Alaska locations: SIT (Sitka), BRW (Barrow), DED (Deadhorse)"
echo "- Colorado/Rocky Mountains: BOU (Boulder)"
echo "- Southwest/Arizona: TUC (Tucson)"
echo "- East Coast/Mid-Atlantic: FRD (Fredericksburg)"
echo "- Hawaii/Pacific: HON (Honolulu)"
echo "- Caribbean: SJG (San Juan)"