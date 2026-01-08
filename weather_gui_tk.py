#!/usr/bin/env python3
"""
Tkinter GUI for weather station data display.
Completely decoupled from the backend - only reads from database.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime, timedelta, timezone
import threading
import time
import json
import os
from typing import List, Tuple

from database import WeatherDatabase


class WeatherGUI:
    """Tkinter GUI for weather station data visualization."""

    def __init__(self, db_path: str = "weather_data.db"):
        self.db_path = db_path
        self.database = WeatherDatabase(db_path)
        self.running = False
        self.refresh_thread = None
        self.use_custom_range = False
        self.custom_start_time = None
        self.custom_end_time = None

        # Chart data caching to improve performance
        self.chart_cache = {
            'last_range': None,
            'weather_data': None,
            'magnetic_flux_data': None,
            'cache_time': None
        }

        # Calibration file path
        self.calibration_file = "weather_station_calibration.json"

        # Default calibration values (NIST SP 330 - SI Units)
        self.default_calibration_values = {
            'wind_speed_counts_per_ms': 3600.0,     # Wind speed: counts per m/s (SI unit)
            'temperature_offset_k': 273.15,         # Temperature: offset to convert °C to K (SI unit)
            'temperature_scale': 1.0,               # Temperature: scale factor
            'humidity_scale': 1.0,                  # Humidity: scale factor (%)
            'humidity_offset': 0.0,                 # Humidity: offset (%)
            'pressure_scale': 1.0,                  # Pressure: scale factor to Pa (SI unit)
            'pressure_offset': 0.0,                 # Pressure: offset in Pa
            'irradiance_scale': 1.0,                # Irradiance: scale factor to W/m² (SI unit)
            'irradiance_offset': 0.0,               # Irradiance: offset in W/m²
            'rain_gauge_mm_per_count': 0.2,         # Rain gauge: mm per count (SI unit)
            # HMC5883L Magnetic Flux Sensor (NIST SP 330 - Tesla SI unit)
            'magnetic_flux_x_scale': 9.174e-8,      # Tesla per LSb (1/(1090 LSb/Gauss * 10000 Gauss/Tesla))
            'magnetic_flux_y_scale': 9.174e-8,      # Tesla per LSb
            'magnetic_flux_z_scale': 9.174e-8,      # Tesla per LSb
            'magnetic_flux_x_offset': 0.0,          # Tesla offset
            'magnetic_flux_y_offset': 0.0,          # Tesla offset
            'magnetic_flux_z_offset': 0.0           # Tesla offset
        }

        # Load calibration values from file or use defaults
        self.calibration_values = self.load_calibration_values()

        # Create main window
        self.root = tk.Tk()
        self.root.title("Weather Station Monitor")
        self.root.geometry("1200x800")

        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.setup_gui()
        self.start_auto_refresh()

    def load_calibration_values(self):
        """Load calibration values from file or return defaults."""
        try:
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)

                # Extract calibration values (handle both old and new format)
                if 'calibration' in data:
                    loaded_values = data['calibration']
                else:
                    loaded_values = data  # Old format compatibility

                # Merge loaded values with defaults (in case new calibration parameters were added)
                calibration_values = self.default_calibration_values.copy()
                calibration_values.update(loaded_values)

                print(f"Loaded calibration values from {self.calibration_file}")
                return calibration_values
            else:
                print(f"No calibration file found, using defaults")
                return self.default_calibration_values.copy()

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading calibration file: {e}. Using defaults.")
            return self.default_calibration_values.copy()

    def save_calibration_values(self):
        """Save current calibration values to file."""
        try:
            # Create a copy with metadata
            calibration_data = {
                'metadata': {
                    'version': '1.0',
                    'created': datetime.now().isoformat(),
                    'description': 'Weather Station Sensor Calibration (NIST SP 330 - SI Units)'
                },
                'calibration': self.calibration_values.copy()
            }

            with open(self.calibration_file, 'w') as f:
                json.dump(calibration_data, f, indent=4)

            print(f"Calibration values saved to {self.calibration_file}")
            return True

        except IOError as e:
            print(f"Error saving calibration file: {e}")
            messagebox.showerror("Save Error",
                               f"Could not save calibration file: {e}")
            return False

    def setup_gui(self):
        """Set up the GUI layout."""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="Weather Station Monitor",
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))

        # Left panel - Current data
        self.setup_current_data_panel(main_frame)

        # Right panel - Charts
        self.setup_charts_panel(main_frame)

        # Bottom panel - Controls
        self.setup_controls_panel(main_frame)

    def setup_current_data_panel(self, parent):
        """Set up the current weather data display panel."""
        # Current weather frame
        current_frame = ttk.LabelFrame(parent, text="Current Weather", padding="10")
        current_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # Weather data labels
        self.weather_vars = {}
        weather_fields = [
            ("Temperature", "°C"),
            ("Humidity", "%"),
            ("Pressure", "hPa"),
            ("Irradiance", ""),
            ("Wind Direction", ""),
            ("Rain Gauge", "count"),
            ("Anemometer", "count"),
            ("Last Updated", "")
        ]

        for i, (field, unit) in enumerate(weather_fields):
            # Field label
            label = ttk.Label(current_frame, text=f"{field}:", font=('Arial', 10, 'bold'))
            label.grid(row=i, column=0, sticky=tk.W, pady=2)

            # Value variable and label
            var = tk.StringVar(value="--")
            self.weather_vars[field.lower().replace(" ", "_")] = var

            value_label = ttk.Label(current_frame, textvariable=var, font=('Arial', 10))
            value_label.grid(row=i, column=1, sticky=tk.W, padx=(10, 0), pady=2)

            # Unit label
            if unit:
                unit_label = ttk.Label(current_frame, text=unit, font=('Arial', 10))
                unit_label.grid(row=i, column=2, sticky=tk.W, padx=(5, 0), pady=2)

        # Statistics frame
        stats_frame = ttk.LabelFrame(current_frame, text="Database Statistics", padding="5")
        stats_frame.grid(row=len(weather_fields), column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        self.stats_vars = {}
        stats_fields = ["Total Weather Records", "Total Flux Records", "Database Size"]

        for i, field in enumerate(stats_fields):
            label = ttk.Label(stats_frame, text=f"{field}:", font=('Arial', 9))
            label.grid(row=i, column=0, sticky=tk.W, pady=1)

            var = tk.StringVar(value="--")
            self.stats_vars[field.lower().replace(" ", "_")] = var

            value_label = ttk.Label(stats_frame, textvariable=var, font=('Arial', 9))
            value_label.grid(row=i, column=1, sticky=tk.W, padx=(10, 0), pady=1)

    def setup_charts_panel(self, parent):
        """Set up the charts panel."""
        charts_frame = ttk.LabelFrame(parent, text="Weather Charts", padding="5")
        charts_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        charts_frame.columnconfigure(0, weight=1)
        charts_frame.rowconfigure(0, weight=1)

        # Create matplotlib figure
        self.fig = Figure(figsize=(8, 6), dpi=80)
        self.fig.patch.set_facecolor('white')

        # Create subplots (will be dynamically created based on selection)
        self.chart_axes = {}
        self.selected_charts = ["Temperature", "Humidity", "Pressure"]  # Default selection

        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, charts_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Add scrollbar for canvas
        scrollbar = ttk.Scrollbar(charts_frame, orient="vertical")
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

    def setup_controls_panel(self, parent):
        """Set up the control buttons panel."""
        controls_frame = ttk.Frame(parent)
        controls_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        # First row of controls
        row1_frame = ttk.Frame(controls_frame)
        row1_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        # Refresh button
        refresh_btn = ttk.Button(row1_frame, text="Refresh Now", command=self.refresh_data)
        refresh_btn.grid(row=0, column=0, padx=(0, 10))

        # Auto-refresh checkbox
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_cb = ttk.Checkbutton(row1_frame, text="Auto-refresh (30s)",
                                         variable=self.auto_refresh_var)
        auto_refresh_cb.grid(row=0, column=1, padx=(0, 10))

        # Time range selection
        ttk.Label(row1_frame, text="Quick Range:").grid(row=0, column=2, padx=(10, 5))

        self.time_range_var = tk.StringVar(value="1 Hour")
        time_range_combo = ttk.Combobox(row1_frame, textvariable=self.time_range_var,
                                       values=["30 Minutes", "1 Hour", "6 Hours", "24 Hours", "7 Days"],
                                       state="readonly", width=12)
        time_range_combo.grid(row=0, column=3, padx=(0, 10))
        time_range_combo.bind('<<ComboboxSelected>>', lambda e: self.on_quick_range_selected())

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(row1_frame, textvariable=self.status_var,
                                font=('Arial', 9), foreground='blue')
        status_label.grid(row=0, column=4, padx=(20, 0))

        # Second row - Custom date range
        row2_frame = ttk.LabelFrame(controls_frame, text="Custom Date Range", padding="5")
        row2_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

        # Custom range checkbox
        self.custom_range_var = tk.BooleanVar(value=False)
        custom_range_cb = ttk.Checkbutton(row2_frame, text="Use custom range",
                                         variable=self.custom_range_var,
                                         command=self.on_custom_range_toggled)
        custom_range_cb.grid(row=0, column=0, padx=(0, 15))

        # Start date/time
        ttk.Label(row2_frame, text="From:").grid(row=0, column=1, padx=(0, 5))

        # Start date picker
        self.start_date_var = tk.StringVar()
        try:
            # Try to use tkcalendar for better date picking
            self.start_date_picker = DateEntry(row2_frame, textvariable=self.start_date_var,
                                             date_pattern='yyyy-mm-dd', width=10)
            self.start_date_picker.set_date(datetime.now().date() - timedelta(days=1))
        except:
            # Fallback to regular entry if tkcalendar not available
            self.start_date_picker = ttk.Entry(row2_frame, textvariable=self.start_date_var, width=12)
            self.start_date_var.set((datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'))

        self.start_date_picker.grid(row=0, column=2, padx=(0, 5))

        # Start time
        self.start_time_var = tk.StringVar(value="00:00")
        start_time_entry = ttk.Entry(row2_frame, textvariable=self.start_time_var, width=8)
        start_time_entry.grid(row=0, column=3, padx=(0, 15))

        # End date/time
        ttk.Label(row2_frame, text="To:").grid(row=0, column=4, padx=(0, 5))

        # End date picker
        self.end_date_var = tk.StringVar()
        try:
            self.end_date_picker = DateEntry(row2_frame, textvariable=self.end_date_var,
                                           date_pattern='yyyy-mm-dd', width=10)
            self.end_date_picker.set_date(datetime.now().date())
        except:
            self.end_date_picker = ttk.Entry(row2_frame, textvariable=self.end_date_var, width=12)
            self.end_date_var.set(datetime.now().strftime('%Y-%m-%d'))

        self.end_date_picker.grid(row=0, column=5, padx=(0, 5))

        # End time
        self.end_time_var = tk.StringVar(value="23:59")
        end_time_entry = ttk.Entry(row2_frame, textvariable=self.end_time_var, width=8)
        end_time_entry.grid(row=0, column=6, padx=(0, 15))

        # Apply custom range button
        apply_btn = ttk.Button(row2_frame, text="Apply Range", command=self.apply_custom_range)
        apply_btn.grid(row=0, column=7, padx=(5, 0))

        # Initially disable custom range controls
        self.toggle_custom_range_controls(False)

        # Third row - Chart selection
        row3_frame = ttk.LabelFrame(controls_frame, text="Chart Selection", padding="5")
        row3_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

        # Chart checkboxes
        self.chart_vars = {}
        chart_options = [
            ("Temperature", "Temperature (°C)"),
            ("Temperature (F)", "Temperature (°F)"),
            ("Humidity", "Humidity (%)"),
            ("Pressure", "Pressure (hPa)"),
            ("Pressure (inHg)", "Pressure (inHg)"),
            ("Wind Speed", "Wind Speed (from anemometer)"),
            ("Wind Direction", "Wind Direction (degrees)"),
            ("Irradiance", "Irradiance/Illuminance"),
            ("Rain Gauge", "Rain Gauge Count"),
            ("Magnetic Flux X", "Magnetic Flux X Component"),
            ("Magnetic Flux Y", "Magnetic Flux Y Component"),
            ("Magnetic Flux Z", "Magnetic Flux Z Component")
        ]

        for i, (chart_id, chart_label) in enumerate(chart_options):
            var = tk.BooleanVar(value=chart_id in self.selected_charts)
            self.chart_vars[chart_id] = var

            cb = ttk.Checkbutton(row3_frame, text=chart_label, variable=var,
                               command=self.on_chart_selection_changed)
            cb.grid(row=i//3, column=i%3, sticky=tk.W, padx=(0, 15), pady=2)

        # Update charts button (place after all checkboxes)
        # Calculate the row after all checkboxes (10 charts in 3 columns = 4 rows needed)
        button_row = (len(chart_options) + 2) // 3  # Ceiling division
        update_charts_btn = ttk.Button(row3_frame, text="Update Charts",
                                     command=self.update_chart_selection)
        update_charts_btn.grid(row=button_row, column=0, columnspan=2, pady=(10, 0))

        # Calibration button
        calibration_btn = ttk.Button(row3_frame, text="Calibration",
                                    command=self.open_calibration_window)
        calibration_btn.grid(row=button_row, column=2, pady=(10, 0), padx=(5, 0))

        # Save PDF button
        save_pdf_btn = ttk.Button(row3_frame, text="Save PDF",
                                  command=self.save_chart_pdf)
        save_pdf_btn.grid(row=button_row + 1, column=0, columnspan=3, pady=(5, 0))

    def toggle_custom_range_controls(self, enabled: bool):
        """Enable or disable custom range controls."""
        state = 'normal' if enabled else 'disabled'
        for widget in [self.start_date_picker, self.end_date_picker]:
            widget.configure(state=state)

    def on_custom_range_toggled(self):
        """Handle custom range checkbox toggle."""
        enabled = self.custom_range_var.get()
        self.toggle_custom_range_controls(enabled)
        self.use_custom_range = enabled

        if not enabled:
            # If custom range is disabled, refresh with quick range
            self.refresh_charts()

    def on_quick_range_selected(self):
        """Handle quick range selection."""
        if not self.custom_range_var.get():
            self.refresh_charts()

    def apply_custom_range(self):
        """Apply the custom date/time range."""
        try:
            # Parse start date/time
            start_date_str = self.start_date_var.get()
            start_time_str = self.start_time_var.get()
            start_datetime_str = f"{start_date_str} {start_time_str}"
            self.custom_start_time = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M')

            # Parse end date/time
            end_date_str = self.end_date_var.get()
            end_time_str = self.end_time_var.get()
            end_datetime_str = f"{end_date_str} {end_time_str}"
            self.custom_end_time = datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M')

            # Validate date range
            if self.custom_start_time >= self.custom_end_time:
                messagebox.showerror("Invalid Range", "Start time must be before end time")
                return

            # Check if range is too large (more than 30 days)
            if (self.custom_end_time - self.custom_start_time).days > 30:
                if not messagebox.askyesno("Large Range Warning",
                                         "Date range is larger than 30 days. This may take time to load. Continue?"):
                    return

            self.use_custom_range = True
            self.refresh_charts()

        except ValueError as e:
            messagebox.showerror("Invalid Date/Time",
                               f"Please enter valid date/time format.\nError: {e}")

    def get_time_range_delta(self):
        """Convert time range selection to timedelta."""
        range_map = {
            "30 Minutes": timedelta(minutes=30),
            "1 Hour": timedelta(hours=1),
            "6 Hours": timedelta(hours=6),
            "24 Hours": timedelta(hours=24),
            "7 Days": timedelta(days=7)
        }
        return range_map.get(self.time_range_var.get(), timedelta(hours=1))

    def get_chart_time_range(self):
        """Get the time range for charts based on current settings.

        Returns UTC times for database queries (created_at is stored in UTC).
        """
        if self.use_custom_range and self.custom_start_time and self.custom_end_time:
            # Custom times are entered as local - convert to UTC for DB query
            start_utc = self.custom_start_time.astimezone(timezone.utc).replace(tzinfo=None)
            end_utc = self.custom_end_time.astimezone(timezone.utc).replace(tzinfo=None)
            return start_utc, end_utc
        else:
            # Use quick range - calculate in UTC for DB query
            time_delta = self.get_time_range_delta()
            end_time = datetime.now(timezone.utc).replace(tzinfo=None)
            start_time = end_time - time_delta
            return start_time, end_time

    def on_chart_selection_changed(self):
        """Handle chart selection checkbox changes."""
        # This is called when any checkbox is clicked
        # We'll update on button press instead for better performance
        pass

    def update_chart_selection(self):
        """Update the selected charts based on checkboxes."""
        self.selected_charts = []
        for chart_id, var in self.chart_vars.items():
            if var.get():
                self.selected_charts.append(chart_id)

        if not self.selected_charts:
            messagebox.showwarning("No Charts Selected",
                                 "Please select at least one chart to display.")
            # Re-enable temperature as default
            self.chart_vars["Temperature"].set(True)
            self.selected_charts = ["Temperature"]

        # Refresh charts with new selection using background thread
        self.refresh_charts_background()

    def calculate_wind_speeds_from_deltas(self, data_dict, times):
        """Calculate wind speeds using delta between consecutive readings."""
        anemometer_counts = data_dict['sample_intervals']  # Temporarily stored counts
        wind_speeds = []

        if len(anemometer_counts) < 2 or len(times) < 2:
            # Not enough data for delta calculation
            data_dict['wind_speeds'] = [0] * len(times)
            return

        # First reading has no previous reading, so wind speed is 0
        wind_speeds.append(0)

        # Calculate wind speed for each subsequent reading
        for i in range(1, len(anemometer_counts)):
            count_delta = anemometer_counts[i] - anemometer_counts[i-1]
            time_delta = (times[i] - times[i-1]).total_seconds()

            if time_delta > 0 and count_delta >= 0:  # Only positive deltas (resets ignored)
                # Convert count delta to wind speed using SI calibration (NIST SP 330)
                # counts_per_ms = how many counts represent 1 m/s (SI unit)
                counts_per_ms = self.calibration_values['wind_speed_counts_per_ms']
                speed_ms = count_delta / (time_delta * counts_per_ms)  # SI unit: m/s
                speed_kmh = speed_ms * 3.6  # Convert to km/h for display (1 m/s = 3.6 km/h)
                wind_speeds.append(speed_kmh)
            else:
                # Invalid time delta or negative count delta (counter reset)
                wind_speeds.append(0)

        data_dict['wind_speeds'] = wind_speeds

    def process_magnetic_flux_data(self, data_dict, times, magnetic_flux_data):
        """Process magnetic flux data and align with weather data timestamps."""
        # Initialize with zeros for all weather data points
        data_dict['magnetic_flux_x'] = [0] * len(times)
        data_dict['magnetic_flux_y'] = [0] * len(times)
        data_dict['magnetic_flux_z'] = [0] * len(times)

        if not magnetic_flux_data:
            return

        # Create a mapping of flux data by timestamp
        flux_by_time = {}
        for flux_row in magnetic_flux_data:
            # flux_row: (x, y, z, created_at)
            # created_at is UTC from SQLite - convert to local time
            timestamp_str = flux_row[3]
            utc_time = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
            timestamp = utc_time.astimezone().replace(tzinfo=None)
            flux_by_time[timestamp] = {
                'x': flux_row[0],
                'y': flux_row[1],
                'z': flux_row[2]
            }

        # Match flux data to weather data timestamps (nearest neighbor)
        for i, weather_time in enumerate(times):
            closest_flux = None
            min_time_diff = float('inf')

            for flux_time, flux_values in flux_by_time.items():
                time_diff = abs((weather_time - flux_time).total_seconds())
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_flux = flux_values

            # Only use flux data if it's within 10 seconds of weather reading
            if closest_flux and min_time_diff <= 10:
                data_dict['magnetic_flux_x'][i] = closest_flux['x']
                data_dict['magnetic_flux_y'][i] = closest_flux['y']
                data_dict['magnetic_flux_z'][i] = closest_flux['z']

    def calculate_wind_speed(self, anemometer_count, sample_interval):
        """Legacy method - now replaced by delta-based calculation."""
        # This method is kept for compatibility but not used
        return 0

    def save_chart_pdf(self):
        """Save the current weather chart as a PDF file."""
        # Generate default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"weather_chart_{timestamp}.pdf"

        # Open file save dialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=default_filename,
            title="Save Weather Chart as PDF"
        )

        if filepath:
            try:
                # Save the figure to PDF
                self.fig.savefig(filepath, format='pdf', bbox_inches='tight', dpi=150)
                messagebox.showinfo("Success", f"Chart saved to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save PDF:\n{str(e)}")

    def open_calibration_window(self):
        """Open the sensor calibration window."""
        # Create calibration window
        cal_window = tk.Toplevel(self.root)
        cal_window.title("Sensor Calibration")
        cal_window.geometry("700x800")
        cal_window.resizable(True, True)

        # Make it modal
        cal_window.transient(self.root)
        cal_window.grab_set()

        # Center the window
        cal_window.update_idletasks()
        x = (cal_window.winfo_screenwidth() // 2) - (700 // 2)
        y = (cal_window.winfo_screenheight() // 2) - (800 // 2)
        cal_window.geometry(f"700x800+{x}+{y}")

        # Create scrollable frame
        canvas = tk.Canvas(cal_window)
        scrollbar = ttk.Scrollbar(cal_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Main frame (now inside scrollable area)
        main_frame = ttk.Frame(scrollable_frame, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Sensor Calibration (NIST SP 330 - SI Units)",
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))

        # Wind Speed Calibration Section
        wind_frame = ttk.LabelFrame(main_frame, text="Wind Speed Sensor (NIST SP 330 - SI Units)", padding="10")
        wind_frame.pack(fill=tk.X, pady=(0, 10))

        # Wind speed calibration input
        ttk.Label(wind_frame, text="Counts per m/s:").grid(row=0, column=0, sticky=tk.W, pady=5)

        # Initialize all calibration variables
        self.wind_speed_cal_var = tk.StringVar(value=str(self.calibration_values['wind_speed_counts_per_ms']))
        self.temp_scale_var = tk.StringVar(value=str(self.calibration_values['temperature_scale']))
        self.temp_offset_var = tk.StringVar(value=str(self.calibration_values['temperature_offset_k']))
        self.humidity_scale_var = tk.StringVar(value=str(self.calibration_values['humidity_scale']))
        self.humidity_offset_var = tk.StringVar(value=str(self.calibration_values['humidity_offset']))
        self.pressure_scale_var = tk.StringVar(value=str(self.calibration_values['pressure_scale']))
        self.pressure_offset_var = tk.StringVar(value=str(self.calibration_values['pressure_offset']))
        self.irradiance_scale_var = tk.StringVar(value=str(self.calibration_values['irradiance_scale']))
        self.irradiance_offset_var = tk.StringVar(value=str(self.calibration_values['irradiance_offset']))
        self.rain_gauge_var = tk.StringVar(value=str(self.calibration_values['rain_gauge_mm_per_count']))

        # Magnetic flux calibration variables (HMC5883L)
        self.magnetic_flux_x_scale_var = tk.StringVar(value=str(self.calibration_values['magnetic_flux_x_scale']))
        self.magnetic_flux_y_scale_var = tk.StringVar(value=str(self.calibration_values['magnetic_flux_y_scale']))
        self.magnetic_flux_z_scale_var = tk.StringVar(value=str(self.calibration_values['magnetic_flux_z_scale']))
        self.magnetic_flux_x_offset_var = tk.StringVar(value=str(self.calibration_values['magnetic_flux_x_offset']))
        self.magnetic_flux_y_offset_var = tk.StringVar(value=str(self.calibration_values['magnetic_flux_y_offset']))
        self.magnetic_flux_z_offset_var = tk.StringVar(value=str(self.calibration_values['magnetic_flux_z_offset']))
        wind_speed_entry = ttk.Entry(wind_frame, textvariable=self.wind_speed_cal_var, width=15)
        wind_speed_entry.grid(row=0, column=1, padx=(10, 0), pady=5)

        # Help text
        help_text = ttk.Label(wind_frame,
                             text="SI calibration: how many anemometer counts\nrepresent 1 m/s of wind speed (NIST SP 330).\nDisplay will show km/h (1 m/s = 3.6 km/h).",
                             font=('Arial', 9),
                             foreground='gray')
        help_text.grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky=tk.W)

        # Temperature Calibration Section
        temp_frame = ttk.LabelFrame(main_frame, text="Temperature Sensor", padding="10")
        temp_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(temp_frame, text="Scale factor:").grid(row=0, column=0, sticky=tk.W, pady=2)
        temp_scale_entry = ttk.Entry(temp_frame, textvariable=self.temp_scale_var, width=15)
        temp_scale_entry.grid(row=0, column=1, padx=(10, 0), pady=2)

        ttk.Label(temp_frame, text="Offset to Kelvin:").grid(row=1, column=0, sticky=tk.W, pady=2)
        temp_offset_entry = ttk.Entry(temp_frame, textvariable=self.temp_offset_var, width=15)
        temp_offset_entry.grid(row=1, column=1, padx=(10, 0), pady=2)

        ttk.Label(temp_frame, text="Formula: K = (sensor_value × scale) + offset",
                 font=('Arial', 9), foreground='gray').grid(row=2, column=0, columnspan=2, pady=(5, 0), sticky=tk.W)

        # Humidity Calibration Section
        humidity_frame = ttk.LabelFrame(main_frame, text="Humidity Sensor", padding="10")
        humidity_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(humidity_frame, text="Scale factor:").grid(row=0, column=0, sticky=tk.W, pady=2)
        humidity_scale_entry = ttk.Entry(humidity_frame, textvariable=self.humidity_scale_var, width=15)
        humidity_scale_entry.grid(row=0, column=1, padx=(10, 0), pady=2)

        ttk.Label(humidity_frame, text="Offset (%):").grid(row=1, column=0, sticky=tk.W, pady=2)
        humidity_offset_entry = ttk.Entry(humidity_frame, textvariable=self.humidity_offset_var, width=15)
        humidity_offset_entry.grid(row=1, column=1, padx=(10, 0), pady=2)

        ttk.Label(humidity_frame, text="Formula: % = (sensor_value × scale) + offset",
                 font=('Arial', 9), foreground='gray').grid(row=2, column=0, columnspan=2, pady=(5, 0), sticky=tk.W)

        # Pressure Calibration Section
        pressure_frame = ttk.LabelFrame(main_frame, text="Pressure Sensor", padding="10")
        pressure_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(pressure_frame, text="Scale factor:").grid(row=0, column=0, sticky=tk.W, pady=2)
        pressure_scale_entry = ttk.Entry(pressure_frame, textvariable=self.pressure_scale_var, width=15)
        pressure_scale_entry.grid(row=0, column=1, padx=(10, 0), pady=2)

        ttk.Label(pressure_frame, text="Offset (Pa):").grid(row=1, column=0, sticky=tk.W, pady=2)
        pressure_offset_entry = ttk.Entry(pressure_frame, textvariable=self.pressure_offset_var, width=15)
        pressure_offset_entry.grid(row=1, column=1, padx=(10, 0), pady=2)

        ttk.Label(pressure_frame, text="SI unit: Pascal (Pa). Display shows hPa (Pa ÷ 100)",
                 font=('Arial', 9), foreground='gray').grid(row=2, column=0, columnspan=2, pady=(5, 0), sticky=tk.W)

        # Irradiance Calibration Section
        irradiance_frame = ttk.LabelFrame(main_frame, text="Irradiance Sensor", padding="10")
        irradiance_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(irradiance_frame, text="Scale factor:").grid(row=0, column=0, sticky=tk.W, pady=2)
        irradiance_scale_entry = ttk.Entry(irradiance_frame, textvariable=self.irradiance_scale_var, width=15)
        irradiance_scale_entry.grid(row=0, column=1, padx=(10, 0), pady=2)

        ttk.Label(irradiance_frame, text="Offset (W/m²):").grid(row=1, column=0, sticky=tk.W, pady=2)
        irradiance_offset_entry = ttk.Entry(irradiance_frame, textvariable=self.irradiance_offset_var, width=15)
        irradiance_offset_entry.grid(row=1, column=1, padx=(10, 0), pady=2)

        ttk.Label(irradiance_frame, text="SI unit: Watts per square meter (W/m²)",
                 font=('Arial', 9), foreground='gray').grid(row=2, column=0, columnspan=2, pady=(5, 0), sticky=tk.W)

        # Rain Gauge Calibration Section
        rain_frame = ttk.LabelFrame(main_frame, text="Rain Gauge Sensor", padding="10")
        rain_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(rain_frame, text="mm per count:").grid(row=0, column=0, sticky=tk.W, pady=2)
        rain_gauge_entry = ttk.Entry(rain_frame, textvariable=self.rain_gauge_var, width=15)
        rain_gauge_entry.grid(row=0, column=1, padx=(10, 0), pady=2)

        ttk.Label(rain_frame, text="Each count represents this many millimeters of rain",
                 font=('Arial', 9), foreground='gray').grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky=tk.W)

        # Magnetic Flux Calibration Section (HMC5883L)
        mag_frame = ttk.LabelFrame(main_frame, text="Magnetic Flux Sensor (HMC5883L) - Tesla SI Units", padding="10")
        mag_frame.pack(fill=tk.X, pady=(0, 10))

        # Create sub-frames for better organization
        scale_frame = ttk.Frame(mag_frame)
        scale_frame.pack(fill=tk.X, pady=(0, 5))

        offset_frame = ttk.Frame(mag_frame)
        offset_frame.pack(fill=tk.X, pady=(0, 5))

        # Scale factors row
        ttk.Label(scale_frame, text="Scale Factors (Tesla/LSb):", font=('Arial', 9, 'bold')).grid(row=0, column=0, columnspan=6, sticky=tk.W, pady=(0, 5))

        ttk.Label(scale_frame, text="X:").grid(row=1, column=0, sticky=tk.W, pady=2)
        mag_x_scale_entry = ttk.Entry(scale_frame, textvariable=self.magnetic_flux_x_scale_var, width=12)
        mag_x_scale_entry.grid(row=1, column=1, padx=(5, 15), pady=2)

        ttk.Label(scale_frame, text="Y:").grid(row=1, column=2, sticky=tk.W, pady=2)
        mag_y_scale_entry = ttk.Entry(scale_frame, textvariable=self.magnetic_flux_y_scale_var, width=12)
        mag_y_scale_entry.grid(row=1, column=3, padx=(5, 15), pady=2)

        ttk.Label(scale_frame, text="Z:").grid(row=1, column=4, sticky=tk.W, pady=2)
        mag_z_scale_entry = ttk.Entry(scale_frame, textvariable=self.magnetic_flux_z_scale_var, width=12)
        mag_z_scale_entry.grid(row=1, column=5, padx=(5, 0), pady=2)

        # Offset values row
        ttk.Label(offset_frame, text="Offset Values (Tesla):", font=('Arial', 9, 'bold')).grid(row=0, column=0, columnspan=6, sticky=tk.W, pady=(0, 5))

        ttk.Label(offset_frame, text="X:").grid(row=1, column=0, sticky=tk.W, pady=2)
        mag_x_offset_entry = ttk.Entry(offset_frame, textvariable=self.magnetic_flux_x_offset_var, width=12)
        mag_x_offset_entry.grid(row=1, column=1, padx=(5, 15), pady=2)

        ttk.Label(offset_frame, text="Y:").grid(row=1, column=2, sticky=tk.W, pady=2)
        mag_y_offset_entry = ttk.Entry(offset_frame, textvariable=self.magnetic_flux_y_offset_var, width=12)
        mag_y_offset_entry.grid(row=1, column=3, padx=(5, 15), pady=2)

        ttk.Label(offset_frame, text="Z:").grid(row=1, column=4, sticky=tk.W, pady=2)
        mag_z_offset_entry = ttk.Entry(offset_frame, textvariable=self.magnetic_flux_z_offset_var, width=12)
        mag_z_offset_entry.grid(row=1, column=5, padx=(5, 0), pady=2)

        # Help text for magnetic flux
        ttk.Label(mag_frame, text="HMC5883L Default: 9.174e-8 T/LSb (1/(1090 LSb/Gauss × 10000 Gauss/Tesla))",
                 font=('Arial', 9), foreground='gray').pack(pady=(5, 0), anchor='w')

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        # Cancel button
        cancel_btn = ttk.Button(button_frame, text="Cancel",
                               command=cal_window.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Apply button
        apply_btn = ttk.Button(button_frame, text="Apply",
                              command=lambda: self.apply_calibration(cal_window))
        apply_btn.pack(side=tk.RIGHT)

        # Focus on the entry field
        wind_speed_entry.focus()
        wind_speed_entry.select_range(0, tk.END)

    def apply_calibration(self, cal_window):
        """Apply calibration values and close the window."""
        try:
            # Validate and update all calibration values

            # Wind speed calibration (SI units)
            new_wind_cal = float(self.wind_speed_cal_var.get())
            if new_wind_cal <= 0:
                messagebox.showerror("Invalid Value", "Wind speed counts per m/s must be positive.")
                return

            # Temperature calibration
            temp_scale = float(self.temp_scale_var.get())
            temp_offset = float(self.temp_offset_var.get())

            # Humidity calibration
            humidity_scale = float(self.humidity_scale_var.get())
            humidity_offset = float(self.humidity_offset_var.get())

            # Pressure calibration
            pressure_scale = float(self.pressure_scale_var.get())
            pressure_offset = float(self.pressure_offset_var.get())

            # Irradiance calibration
            irradiance_scale = float(self.irradiance_scale_var.get())
            irradiance_offset = float(self.irradiance_offset_var.get())

            # Rain gauge calibration
            rain_gauge_cal = float(self.rain_gauge_var.get())
            if rain_gauge_cal <= 0:
                messagebox.showerror("Invalid Value", "Rain gauge mm per count must be positive.")
                return

            # Magnetic flux calibration (HMC5883L)
            mag_x_scale = float(self.magnetic_flux_x_scale_var.get())
            mag_y_scale = float(self.magnetic_flux_y_scale_var.get())
            mag_z_scale = float(self.magnetic_flux_z_scale_var.get())
            mag_x_offset = float(self.magnetic_flux_x_offset_var.get())
            mag_y_offset = float(self.magnetic_flux_y_offset_var.get())
            mag_z_offset = float(self.magnetic_flux_z_offset_var.get())

            # Update all calibration values
            self.calibration_values.update({
                'wind_speed_counts_per_ms': new_wind_cal,
                'temperature_scale': temp_scale,
                'temperature_offset_k': temp_offset,
                'humidity_scale': humidity_scale,
                'humidity_offset': humidity_offset,
                'pressure_scale': pressure_scale,
                'pressure_offset': pressure_offset,
                'irradiance_scale': irradiance_scale,
                'irradiance_offset': irradiance_offset,
                'rain_gauge_mm_per_count': rain_gauge_cal,
                'magnetic_flux_x_scale': mag_x_scale,
                'magnetic_flux_y_scale': mag_y_scale,
                'magnetic_flux_z_scale': mag_z_scale,
                'magnetic_flux_x_offset': mag_x_offset,
                'magnetic_flux_y_offset': mag_y_offset,
                'magnetic_flux_z_offset': mag_z_offset
            })

            # Save calibration values to file
            if self.save_calibration_values():
                save_msg = "\nCalibration values saved to file for future sessions."
            else:
                save_msg = "\nWarning: Could not save calibration values to file."

            # Close the window
            cal_window.destroy()

            # Show confirmation
            messagebox.showinfo("Calibration Updated",
                              "All sensor calibrations updated successfully.\n"
                              "Charts will use the new calibrations on next refresh.\n"
                              "All values follow NIST SP 330 SI units standard." + save_msg)

            # Refresh charts with new calibrations
            self.refresh_charts()

        except ValueError:
            messagebox.showerror("Invalid Value",
                               "Please enter valid numbers for all calibration values.")

    def refresh_data(self):
        """Refresh all displayed data."""
        try:
            self.status_var.set("Refreshing...")
            self.root.update()

            # Update current weather (fast)
            self.update_current_weather()

            # Update statistics (fast)
            self.update_statistics()

            # Update charts in background to prevent UI blocking
            self.refresh_charts_background()

        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            print(f"Error refreshing data: {e}")

    def refresh_charts_background(self):
        """Start chart refresh in background thread to prevent UI blocking."""
        def background_refresh():
            try:
                self.root.after(0, lambda: self.status_var.set("Loading charts..."))

                # Run chart refresh in background
                self.refresh_charts()

                # Update status on main thread
                self.root.after(0, lambda: self.status_var.set(f"Last updated: {datetime.now().strftime('%H:%M:%S')}"))

            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Chart error: {str(e)}"))
                print(f"Error in background chart refresh: {e}")

        # Start background thread
        threading.Thread(target=background_refresh, daemon=True).start()

    def update_current_weather(self):
        """Update current weather display."""
        try:
            summary = self.database.get_current_weather_summary()
            if summary:
                self.weather_vars["temperature"].set(f"{summary.get('temperature', '--'):.1f}" if summary.get('temperature') else "--")
                self.weather_vars["humidity"].set(f"{summary.get('humidity', '--'):.1f}" if summary.get('humidity') else "--")
                self.weather_vars["pressure"].set(f"{summary.get('pressure', '--'):.1f}" if summary.get('pressure') else "--")
                self.weather_vars["irradiance"].set(f"{summary.get('irradiance', '--'):.3f}" if summary.get('irradiance') else "--")
                self.weather_vars["wind_direction"].set(str(summary.get('wind_direction', '--')))
                self.weather_vars["rain_gauge"].set(str(summary.get('rain_gauge_count', '--')))
                self.weather_vars["anemometer"].set(str(summary.get('anemometer_count', '--')))

                if summary.get('last_updated'):
                    # Parse the timestamp (UTC) and convert to local time
                    try:
                        utc_time = datetime.fromisoformat(summary['last_updated']).replace(tzinfo=timezone.utc)
                        local_time = utc_time.astimezone().replace(tzinfo=None)
                        formatted_time = local_time.strftime('%Y-%m-%d %H:%M:%S')
                        self.weather_vars["last_updated"].set(formatted_time)
                    except:
                        self.weather_vars["last_updated"].set(summary['last_updated'])
            else:
                for var in self.weather_vars.values():
                    var.set("--")

        except Exception as e:
            print(f"Error updating current weather: {e}")

    def update_statistics(self):
        """Update database statistics."""
        try:
            import os

            # Get record counts (simplified method)
            weather_data = self.database.get_latest_weather_data(1000)  # Get up to 1000 recent records
            flux_data = self.database.get_latest_magnetic_flux_data(1000)

            self.stats_vars["total_weather_records"].set(f"{len(weather_data):,}")
            self.stats_vars["total_flux_records"].set(f"{len(flux_data):,}")

            # Get database file size
            if os.path.exists(self.db_path):
                size_bytes = os.path.getsize(self.db_path)
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024*1024:
                    size_str = f"{size_bytes/1024:.1f} KB"
                else:
                    size_str = f"{size_bytes/(1024*1024):.1f} MB"
                self.stats_vars["database_size"].set(size_str)
            else:
                self.stats_vars["database_size"].set("N/A")

        except Exception as e:
            print(f"Error updating statistics: {e}")

    def refresh_charts(self):
        """Refresh the weather charts based on selected chart types."""
        try:
            # Clear the figure
            self.fig.clear()
            self.chart_axes = {}

            if not self.selected_charts:
                self.canvas.draw()
                return

            # Get time range based on current settings
            start_time, end_time = self.get_chart_time_range()
            current_range = (start_time, end_time)

            # Check cache to avoid unnecessary database queries
            cache_valid = (
                self.chart_cache['last_range'] == current_range and
                self.chart_cache['cache_time'] and
                (datetime.now() - self.chart_cache['cache_time']).total_seconds() < 30  # 30-second cache
            )

            if cache_valid and not self.use_custom_range:
                # Use cached data for automatic refreshes
                weather_data = self.chart_cache['weather_data']
                magnetic_flux_data = self.chart_cache['magnetic_flux_data']
                print("Using cached chart data")
            else:
                # Calculate intelligent sampling based on time range
                time_span = end_time - start_time
                max_points = 2000  # Maximum data points for chart performance
                sample_interval = 1
                data_limit = None

                # Estimate data points based on 5-second intervals (typical MQTT rate)
                estimated_points = int(time_span.total_seconds() / 5)

                if estimated_points > max_points:
                    # Use sampling to reduce data points
                    sample_interval = max(1, estimated_points // max_points)
                    print(f"Large dataset detected ({estimated_points} points), using sample interval: {sample_interval}")
                elif estimated_points > max_points * 2:
                    # For very large datasets, use both sampling and limits
                    sample_interval = max(1, estimated_points // max_points)
                    data_limit = max_points
                    print(f"Very large dataset detected, using sample interval: {sample_interval} and limit: {data_limit}")

                # Get data for the time range with optimizations
                weather_data = self.database.get_weather_data_range(start_time, end_time,
                                                                  limit=data_limit,
                                                                  sample_interval=sample_interval)
                magnetic_flux_data = self.database.get_magnetic_flux_data_range(start_time, end_time,
                                                                               limit=data_limit,
                                                                               sample_interval=sample_interval)

                # Update cache
                self.chart_cache.update({
                    'last_range': current_range,
                    'weather_data': weather_data,
                    'magnetic_flux_data': magnetic_flux_data,
                    'cache_time': datetime.now()
                })

            if weather_data:
                # Parse data
                times = []
                data_dict = {
                    'temperatures': [],
                    'temperatures_f': [],
                    'humidities': [],
                    'pressures': [],
                    'pressures_inhg': [],
                    'irradiances': [],
                    'wind_directions': [],
                    'wind_speeds': [],
                    'sample_intervals': [],
                    'rain_gauge_counts': [],
                    'magnetic_flux_x': [],
                    'magnetic_flux_y': [],
                    'magnetic_flux_z': []
                }

                for row in weather_data:
                    try:
                        # Convert Unix timestamp (UTC) to local time
                        timestamp = datetime.fromtimestamp(row[0])
                        times.append(timestamp)

                        # Extract all data fields
                        temp_c = row[1]  # temperature in Celsius
                        data_dict['temperatures'].append(temp_c)
                        data_dict['temperatures_f'].append(temp_c * 9/5 + 32 if temp_c is not None else None)  # Fahrenheit
                        data_dict['humidities'].append(row[2])    # humidity
                        pressure_hpa = row[3]  # pressure in hPa
                        data_dict['pressures'].append(pressure_hpa)
                        data_dict['pressures_inhg'].append(pressure_hpa * 0.02953 if pressure_hpa is not None else None)  # inHg
                        data_dict['irradiances'].append(row[4])   # irradiance
                        data_dict['wind_directions'].append(row[5])  # wind_direction
                        data_dict['rain_gauge_counts'].append(row[6])  # rain_gauge_count

                        # Store anemometer count for later delta calculation
                        anemometer_count = row[7] if row[7] else 0  # anemometer_count
                        data_dict['sample_intervals'].append(anemometer_count)  # Store counts temporarily

                    except (ValueError, IndexError) as e:
                        continue  # Skip invalid data points

                # Calculate wind speeds using delta between consecutive readings
                self.calculate_wind_speeds_from_deltas(data_dict, times)

                # Process magnetic flux data
                self.process_magnetic_flux_data(data_dict, times, magnetic_flux_data)

                if times:
                    # Create subplots based on selected charts
                    num_charts = len(self.selected_charts)
                    chart_configs = {
                        'Temperature': {'data': data_dict['temperatures'], 'color': 'red', 'ylabel': 'Temperature (°C)'},
                        'Temperature (F)': {'data': data_dict['temperatures_f'], 'color': 'red', 'ylabel': 'Temperature (°F)'},
                        'Humidity': {'data': data_dict['humidities'], 'color': 'blue', 'ylabel': 'Humidity (%)'},
                        'Pressure': {'data': data_dict['pressures'], 'color': 'green', 'ylabel': 'Pressure (hPa)'},
                        'Pressure (inHg)': {'data': data_dict['pressures_inhg'], 'color': 'green', 'ylabel': 'Pressure (inHg)'},
                        'Irradiance': {'data': data_dict['irradiances'], 'color': 'orange', 'ylabel': 'Irradiance'},
                        'Wind Direction': {'data': data_dict['wind_directions'], 'color': 'purple', 'ylabel': 'Wind Direction (°)'},
                        'Wind Speed': {'data': data_dict['wind_speeds'], 'color': 'brown', 'ylabel': 'Wind Speed (km/h)'},
                        'Rain Gauge': {'data': data_dict['rain_gauge_counts'], 'color': 'darkgreen', 'ylabel': 'Rain Gauge Count'},
                        'Magnetic Flux X': {'data': data_dict['magnetic_flux_x'], 'color': 'cyan', 'ylabel': 'Magnetic Flux X'},
                        'Magnetic Flux Y': {'data': data_dict['magnetic_flux_y'], 'color': 'magenta', 'ylabel': 'Magnetic Flux Y'},
                        'Magnetic Flux Z': {'data': data_dict['magnetic_flux_z'], 'color': 'darkblue', 'ylabel': 'Magnetic Flux Z'}
                    }

                    # Create subplots
                    for i, chart_type in enumerate(self.selected_charts):
                        ax = self.fig.add_subplot(num_charts, 1, i + 1)
                        self.chart_axes[chart_type] = ax

                        config = chart_configs[chart_type]

                        if chart_type == 'Wind Direction':
                            # Special handling for wind direction - use scatter plot with direction indicators
                            ax.scatter(times, config['data'], c=config['color'], alpha=0.6, s=20)
                            ax.set_ylim(0, 360)
                            ax.set_yticks([0, 90, 180, 270, 360])
                            ax.set_yticklabels(['N', 'E', 'S', 'W', 'N'])
                        else:
                            # Regular line plot
                            ax.plot(times, config['data'], color=config['color'], linewidth=1.5)

                        ax.set_ylabel(config['ylabel'], fontsize=10)
                        ax.grid(True, alpha=0.3)
                        ax.tick_params(axis='x', labelsize=8)
                        ax.tick_params(axis='y', labelsize=8)

                        # Only show x-axis label on the bottom chart
                        if i == num_charts - 1:
                            ax.set_xlabel('Time', fontsize=10)

                    # Format x-axis based on time range
                    time_span = end_time - start_time
                    if time_span.days > 1:
                        date_format = '%m/%d %H:%M'
                        if time_span.days > 7:
                            date_format = '%m/%d'
                            locator = mdates.DayLocator(interval=max(1, time_span.days // 10))
                        else:
                            locator = mdates.HourLocator(interval=max(1, int(time_span.total_seconds() / 3600 / 8)))
                    else:
                        date_format = '%H:%M'
                        locator = mdates.HourLocator(interval=max(1, int(time_span.total_seconds() / 3600 / 6)))

                    # Apply formatting to all axes
                    for ax in self.chart_axes.values():
                        ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
                        ax.xaxis.set_major_locator(locator)

                    # Set title on the top chart
                    if self.selected_charts:
                        top_ax = self.chart_axes[self.selected_charts[0]]
                        if self.use_custom_range:
                            title = f'Weather Data - {start_time.strftime("%Y-%m-%d %H:%M")} to {end_time.strftime("%Y-%m-%d %H:%M")}'
                        else:
                            title = f'Weather Data - Last {self.time_range_var.get()}'
                        top_ax.set_title(title, fontsize=12)

            else:
                # No data available
                ax = self.fig.add_subplot(1, 1, 1)
                ax.text(0.5, 0.5, 'No data available for selected time range',
                       ha='center', va='center', transform=ax.transAxes)

            # Adjust layout and redraw (ensure this runs on main thread)
            def update_ui():
                self.fig.tight_layout()
                self.canvas.draw()

            if threading.current_thread() == threading.main_thread():
                update_ui()
            else:
                self.root.after(0, update_ui)

        except Exception as e:
            print(f"Error refreshing charts: {e}")
            import traceback
            traceback.print_exc()

    def start_auto_refresh(self):
        """Start the auto-refresh thread."""
        self.running = True
        self.refresh_thread = threading.Thread(target=self.auto_refresh_worker, daemon=True)
        self.refresh_thread.start()

        # Initial data load
        self.refresh_data()

    def auto_refresh_worker(self):
        """Worker thread for auto-refresh."""
        while self.running:
            time.sleep(30)  # Refresh every 30 seconds
            if self.running and self.auto_refresh_var.get():
                try:
                    # Only auto-refresh if not using custom range
                    # Custom ranges should be manually refreshed
                    if not self.use_custom_range:
                        # Schedule refresh in main thread
                        self.root.after(0, self.refresh_data)
                    else:
                        # Just update current weather data, not charts
                        self.root.after(0, self.update_current_weather)
                        self.root.after(0, self.update_statistics)
                except:
                    break

    def on_closing(self):
        """Handle window closing."""
        self.running = False
        if self.refresh_thread:
            self.refresh_thread.join(timeout=1)
        self.root.destroy()

    def run(self):
        """Run the GUI application."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Weather Station Tkinter GUI")
    parser.add_argument("--db", default="/deepsink1/weatherstation/data/weather_data.db",
                        help="Database file path (default: /deepsink1/weatherstation/data/weather_data.db)")

    args = parser.parse_args()

    try:
        app = WeatherGUI(args.db)
        app.run()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start GUI: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()