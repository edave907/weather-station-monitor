#!/bin/bash
# Examples for using the Magnetic Flux 3D Plotter

echo "Magnetic Flux 3D Visualization Examples"
echo "======================================="
echo

# Make sure we have the required dependencies
if ! python -c "import numpy, matplotlib" 2>/dev/null; then
    echo "Installing required dependencies..."
    ./venv/bin/pip install numpy matplotlib
fi

echo "1. Quick visualization of last hour (interactive):"
echo "   python magnetic_flux_3d_plotter.py --hours 1"
echo

echo "2. Save all plots for last 6 hours:"
echo "   python magnetic_flux_3d_plotter.py --hours 6 --save --output-dir magnetic_plots/"
echo

echo "3. Only magnitude and direction plots for specific date range:"
echo "   python magnetic_flux_3d_plotter.py --start \"2025-10-03 10:00\" --end \"2025-10-03 18:00\" --plots magnitude direction --save"
echo
echo "4. 2D polar plot showing XY plane magnetic field direction:"
echo "   python magnetic_flux_3d_plotter.py --hours 6 --plots polar --save"
echo

echo "5. High-quality PDF plots for last day:"
echo "   python magnetic_flux_3d_plotter.py --hours 24 --save --format pdf --output-dir publication_plots/"
echo

echo "6. Quick statistical summary without plots:"
echo "   python magnetic_flux_3d_plotter.py --hours 12 --plots magnitude --no-stats"
echo

echo "Running a quick demo with last hour's data..."
echo "=============================================="

# Run a demo with the last hour including the new polar plot
./venv/bin/python magnetic_flux_3d_plotter.py --hours 1 --plots magnitude polar --save --output-dir demo_plots/

echo
echo "Demo plots saved to demo_plots/"
echo "You can view them with your preferred image viewer."
echo
echo "For interactive plots (recommended), run without --save:"
echo "python magnetic_flux_3d_plotter.py --hours 1"