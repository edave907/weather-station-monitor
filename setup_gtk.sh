#!/bin/bash
# Setup script for GTK GUI support

echo "Setting up GTK GUI support for Weather Station..."

# Check if we can use system Python 3.11 with GTK
if /usr/bin/python3.11 -c "import gi" 2>/dev/null; then
    echo "✓ GTK available in system Python 3.11"

    # Install required packages for system Python
    echo "Installing required packages for system Python..."
    /usr/bin/python3.11 -m pip install --user paho-mqtt matplotlib numpy

    if [ $? -eq 0 ]; then
        echo "✓ Packages installed successfully"
        echo ""
        echo "You can now run the GTK GUI with:"
        echo "  /usr/bin/python3.11 run_gui.py"
        echo ""
        echo "Or continue using the virtual environment for console mode:"
        echo "  ./venv/bin/python main.py --console"
    else
        echo "✗ Failed to install packages"
        exit 1
    fi
else
    echo "✗ GTK not available in system Python"
    echo "Please install GTK support:"
    echo "  sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0"
    exit 1
fi