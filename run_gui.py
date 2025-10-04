#!/usr/bin/python3.11
"""
GTK GUI launcher that uses system Python for GTK support.
This script runs outside the virtual environment to access system GTK packages.
"""

import sys
import os

# Add the project directory to Python path to import our modules
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Add venv site-packages for other dependencies
venv_site_packages = os.path.join(project_dir, 'venv', 'lib', 'python3.12', 'site-packages')
if os.path.exists(venv_site_packages):
    sys.path.insert(0, venv_site_packages)

try:
    # Test GTK availability
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    print("GTK is available via system Python")

    # Import our application
    from weather_gui import WeatherGUI

    # Run the GUI
    app = WeatherGUI()
    app.run()

except ImportError as e:
    print(f"GTK not available: {e}")
    print("Falling back to console mode...")

    # Fall back to console mode
    from weather_gui import SimpleWeatherDisplay
    app = SimpleWeatherDisplay()
    app.run()

except Exception as e:
    print(f"Error running GUI: {e}")
    sys.exit(1)