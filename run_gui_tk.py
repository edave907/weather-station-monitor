#!/usr/bin/env python3
"""
Simple launcher for the Tkinter weather GUI.
This script can be run independently of the daemon.
"""

import sys
import os

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Add venv site-packages for dependencies
venv_site_packages = os.path.join(project_dir, 'venv', 'lib', 'python3.12', 'site-packages')
if os.path.exists(venv_site_packages):
    sys.path.insert(0, venv_site_packages)

try:
    # Import and run the Tkinter GUI
    from weather_gui_tk import WeatherGUI
    import argparse

    parser = argparse.ArgumentParser(description="Weather Station Tkinter GUI")
    parser.add_argument("--db", default="/deepsink1/weatherstation/data/weather_data.db",
                        help="Database file path (default: /deepsink1/weatherstation/data/weather_data.db)")

    args = parser.parse_args()

    print("Starting Tkinter Weather GUI...")
    print(f"Database: {args.db}")

    app = WeatherGUI(args.db)
    app.run()

except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all dependencies are installed:")
    print("  pip install matplotlib tkcalendar")
    sys.exit(1)

except Exception as e:
    print(f"Error starting GUI: {e}")
    sys.exit(1)