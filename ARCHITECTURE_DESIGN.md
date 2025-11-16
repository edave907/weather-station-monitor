# Weather Station Architecture Design

## Project Modularization and Configuration Strategy

### Current Status
The weather station project has evolved from a simple MQTT data collector to a comprehensive system with GUI interfaces, 3D visualization, USGS data integration, and NIST SP 330 compliance. This document outlines the planned modular architecture for future development.

## Configuration Strategy

### Configuration Format Decision: JSON
**Decision**: Use JSON for all configuration files to maintain consistency with existing calibration system.

**Rationale**:
- Already using `weather_station_calibration.json`
- Native Python support (no dependencies)
- Universal compatibility
- Smaller file sizes than YAML
- Less error-prone than YAML indentation

**When to consider YAML**: Only for complex user-editable configurations with extensive documentation needs.

## Modular Project Structure

### Recommended Directory Organization

```
weatherstation/
├── config/
│   ├── weather_station_config.json     # Main runtime configuration
│   ├── sensors_config.json             # All sensor settings
│   ├── charts_config.json              # Chart/visualization settings
│   ├── gui_config.json                 # Window states & layout
│   └── usgs_config.json                # USGS integration settings
│
├── sensors/
│   ├── __init__.py
│   ├── base_sensor.py                  # Abstract sensor interface
│   ├── hmc5883l.py                     # Magnetic flux sensor
│   ├── weather_meters.py               # Temperature, humidity, etc.
│   └── calibration.py                  # Sensor calibration utilities
│
├── charts/
│   ├── __init__.py
│   ├── base_chart.py                   # Chart interface
│   ├── chart_manager.py                # Undocking/docking logic
│   ├── weather_charts.py               # Temperature, pressure plots
│   ├── magnetic_charts.py              # 3D magnetic flux plots
│   ├── comparison_charts.py            # USGS comparison plots
│   └── window_manager.py               # Window state persistence
│
├── data/
│   ├── __init__.py
│   ├── database.py                     # Database interface
│   ├── mqtt_client.py                  # MQTT data collection
│   └── usgs_importer.py                # USGS data import
│
├── gui/
│   ├── __init__.py
│   ├── main_window.py                  # Root window
│   ├── chart_container.py              # Dockable chart area
│   ├── menu_bar.py                     # Chart → Undock menu
│   ├── tkinter_gui.py                  # Main Tkinter interface
│   ├── widgets/                        # Custom GUI components
│   └── dialogs/                        # Calibration dialogs, etc.
│       └── chart_preferences.py        # Chart layout settings
│
└── utils/
    ├── __init__.py
    ├── config_manager.py               # Configuration loading/saving
    ├── units.py                        # NIST SP 330 unit conversions
    └── logging_setup.py                # Logging configuration
```

## Configuration File Structures

### Main Configuration (`config/weather_station_config.json`)
```json
{
  "version": "2.0",
  "created": "2025-10-05",
  "mqtt": {
    "host": "localhost",
    "port": 1883,
    "keepalive": 60,
    "topics": {
      "weather": "backacres/house/weatherstation/weathermeters/",
      "magnetic": "backacres/house/weatherstation/magneticfluxsensor/"
    }
  },
  "database": {
    "path": "weather_data.db",
    "backup_interval_hours": 24,
    "vacuum_interval_days": 7
  },
  "logging": {
    "level": "INFO",
    "file": "weather_daemon.log",
    "max_size_mb": 10,
    "backup_count": 5
  }
}
```

### Sensor Configuration (`config/sensors_config.json`)
```json
{
  "hmc5883l": {
    "enabled": true,
    "mqtt_topic": "backacres/house/weatherstation/magneticfluxsensor/",
    "calibration_file": "weather_station_calibration.json",
    "sample_rate_ms": 5000,
    "range": "±8_gauss",
    "scale_factor": 9.174e-8,
    "validation": {
      "min_field_strength_nt": 20000,
      "max_field_strength_nt": 70000,
      "max_component_change_nt": 1000
    }
  },
  "weather_meters": {
    "enabled": true,
    "mqtt_topic": "backacres/house/weatherstation/weathermeters/",
    "sensors": {
      "temperature": {
        "enabled": true,
        "unit": "celsius",
        "range": {"min": -40, "max": 85},
        "precision": 0.1
      },
      "humidity": {
        "enabled": true,
        "unit": "percent",
        "range": {"min": 0, "max": 100},
        "precision": 0.1
      },
      "pressure": {
        "enabled": true,
        "unit": "hPa",
        "range": {"min": 300, "max": 1100},
        "precision": 0.01
      },
      "wind_speed": {
        "enabled": true,
        "unit": "m/s",
        "calculation_method": "delta_based",
        "time_window_seconds": 60
      },
      "wind_direction": {
        "enabled": true,
        "unit": "degrees",
        "magnetic_declination": 0.0
      }
    }
  }
}
```

### Chart Configuration (`config/charts_config.json`)
```json
{
  "general": {
    "max_data_points": 2000,
    "cache_duration_seconds": 30,
    "default_dpi": 150,
    "auto_refresh_interval_seconds": 30
  },
  "weather_charts": {
    "temperature": {
      "color": "red",
      "line_width": 1.5,
      "show_grid": true,
      "y_axis_unit": "°C"
    },
    "humidity": {
      "color": "blue",
      "line_width": 1.5,
      "show_grid": true,
      "y_axis_unit": "%"
    },
    "pressure": {
      "color": "green",
      "line_width": 1.5,
      "show_grid": true,
      "y_axis_unit": "hPa"
    },
    "wind_speed": {
      "color": "orange",
      "line_width": 1.5,
      "show_grid": true,
      "y_axis_unit": "m/s"
    }
  },
  "magnetic_charts": {
    "3d_plots": {
      "enabled": true,
      "vector_scale": 1000,
      "colormap": "viridis",
      "show_earth_field_reference": true,
      "units": "microtesla"
    },
    "polar_plots": {
      "enabled": true,
      "grid": true,
      "compass_labels": true,
      "show_statistics": true
    },
    "time_series": {
      "components": ["x", "y", "z", "magnitude"],
      "colors": {"x": "red", "y": "green", "z": "blue", "magnitude": "black"}
    }
  },
  "comparison_charts": {
    "correlation_threshold": 0.8,
    "difference_tolerance_percent": 5.0,
    "time_alignment_minutes": 5,
    "show_statistics_overlay": true
  }
}
```

### GUI Configuration (`config/gui_config.json`)
```json
{
  "main_window": {
    "title": "Weather Station Monitor",
    "width": 1200,
    "height": 800,
    "position": {"x": 100, "y": 100},
    "min_width": 800,
    "min_height": 600
  },
  "chart_windows": {
    "temperature_chart": {
      "undocked": false,
      "width": 600,
      "height": 400,
      "position": {"x": 200, "y": 200},
      "always_on_top": false,
      "auto_refresh": true,
      "resizable": true
    },
    "magnetic_3d_chart": {
      "undocked": false,
      "width": 800,
      "height": 600,
      "position": {"x": 400, "y": 300},
      "always_on_top": false,
      "auto_refresh": true,
      "resizable": true
    },
    "usgs_comparison_chart": {
      "undocked": false,
      "width": 1000,
      "height": 700,
      "position": {"x": 300, "y": 250},
      "always_on_top": false,
      "auto_refresh": false,
      "resizable": true
    }
  },
  "chart_layout": {
    "docked_arrangement": "grid",
    "columns": 2,
    "spacing": 10,
    "padding": 5
  },
  "preferences": {
    "theme": "default",
    "font_size": 10,
    "save_window_states": true,
    "confirm_chart_undocking": false
  }
}
```

### USGS Configuration (`config/usgs_config.json`)
```json
{
  "api": {
    "base_url": "https://geomag.usgs.gov/ws/data/",
    "timeout_seconds": 30,
    "retry_attempts": 3,
    "rate_limit_delay_seconds": 0.5
  },
  "default_observatory": "BOU",
  "observatories": {
    "BOU": {"name": "Boulder", "state": "Colorado", "recommended_for": ["western_us", "rocky_mountains"]},
    "FRD": {"name": "Fredericksburg", "state": "Virginia", "recommended_for": ["eastern_us", "mid_atlantic"]},
    "TUC": {"name": "Tucson", "state": "Arizona", "recommended_for": ["southwest_us"]},
    "HON": {"name": "Honolulu", "state": "Hawaii", "recommended_for": ["pacific", "hawaii"]},
    "SJG": {"name": "San Juan", "state": "Puerto Rico", "recommended_for": ["caribbean"]}
  },
  "import_settings": {
    "default_time_range_hours": 24,
    "chunk_size_hours": 24,
    "max_import_days": 365,
    "cache_duration_hours": 24
  },
  "comparison_settings": {
    "time_alignment_tolerance_minutes": 5,
    "correlation_threshold": 0.8,
    "auto_select_nearest_observatory": false
  }
}
```

## Undockable Charts Architecture

### Key Requirements
- Charts can be undocked from main window into independent windows
- Window states persist between sessions
- Independent resizing and positioning
- Coordinated data refresh across all windows
- Context menus for docking/undocking
- Multi-monitor support

### Implementation Strategy

#### Chart Manager Interface
```python
# charts/chart_manager.py
class ChartManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.docked_charts = {}      # Charts in main window
        self.undocked_charts = {}    # Independent chart windows
        self.chart_configs = {}      # Persistent window states

    def undock_chart(self, chart_id):
        """Move chart from main window to independent window"""

    def dock_chart(self, chart_id):
        """Move chart from independent window to main window"""

    def save_all_window_states(self):
        """Save current window positions/sizes for persistence"""

    def restore_window_states(self):
        """Restore saved window states on application startup"""
```

#### Base Chart Interface
```python
# charts/base_chart.py
class BaseChart:
    def __init__(self, chart_id, title, config_manager):
        self.chart_id = chart_id
        self.title = title
        self.config = config_manager.load_chart_config(chart_id)
        self.parent_container = None
        self.is_undocked = False

    def attach_to_container(self, container):
        """Attach chart to main window container"""

    def detach_to_window(self, window):
        """Move chart to independent window"""

    def refresh(self):
        """Update chart with latest data"""

    def save_window_state(self):
        """Save current window position/size"""

    def create_context_menu(self):
        """Create right-click menu for chart operations"""
```

### Context Menu Integration
- Right-click on docked chart: "Undock to New Window"
- Right-click on undocked chart: "Dock to Main Window", "Always on Top"
- Menu options: Chart Settings, Export, Close

### Chart-Specific Configuration System
Each chart has its own configuration button with parameters specific to that chart type, while inheriting global configuration items.

#### Configuration Inheritance Hierarchy
```
Global Chart Config (charts_config.json)
    ↓ (inherited by)
Chart Type Config (e.g., weather_charts.temperature)
    ↓ (inherited by)
Chart Instance Config (e.g., temperature_chart_main_window)
```

#### Chart Configuration Button Interface
```python
# charts/base_chart.py
class BaseChart:
    def create_config_button(self):
        """Create configuration button for chart-specific settings"""
        config_btn = tk.Button(
            self.header_frame,
            text="⚙️",
            command=self.show_config_dialog,
            width=3,
            relief=tk.FLAT
        )
        config_btn.pack(side=tk.RIGHT, padx=2)

    def show_config_dialog(self):
        """Show chart-specific configuration dialog"""
        dialog = ChartConfigDialog(
            parent=self.parent_container,
            chart_id=self.chart_id,
            chart_config=self.config,
            global_config=self.global_config
        )

        if dialog.result:
            self.update_config(dialog.result)
            self.refresh()
```

#### Chart Configuration Dialog
```python
# gui/dialogs/chart_config_dialog.py
class ChartConfigDialog:
    def __init__(self, parent, chart_id, chart_config, global_config):
        self.chart_id = chart_id
        self.chart_config = chart_config.copy()  # Local copy for editing
        self.global_config = global_config
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Configure {chart_id}")
        self.dialog.geometry("400x500")

        self.create_tabs()

    def create_tabs(self):
        """Create tabbed interface for different config categories"""
        notebook = ttk.Notebook(self.dialog)

        # Chart-specific settings tab
        self.create_chart_specific_tab(notebook)

        # Visual settings tab
        self.create_visual_settings_tab(notebook)

        # Data settings tab
        self.create_data_settings_tab(notebook)

        # Advanced settings tab
        self.create_advanced_settings_tab(notebook)

        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
```

#### Enhanced Chart Configuration Structure

##### Chart Instance Configuration (`config/chart_instances.json`)
```json
{
  "temperature_chart_main": {
    "chart_type": "weather_charts.temperature",
    "title": "Temperature Sensor",
    "position": {"row": 0, "column": 0},
    "size": {"width": 400, "height": 300},
    "specific_config": {
      "temperature_unit": "celsius",
      "show_trend_line": true,
      "trend_period_minutes": 60,
      "alert_thresholds": {
        "low": -10.0,
        "high": 40.0,
        "enabled": true
      },
      "y_axis": {
        "auto_scale": true,
        "min_value": null,
        "max_value": null,
        "show_grid": true,
        "grid_style": "dotted"
      },
      "data_processing": {
        "smoothing": false,
        "smoothing_window": 5,
        "outlier_detection": true,
        "outlier_threshold": 3.0
      }
    }
  },
  "magnetic_3d_chart_main": {
    "chart_type": "magnetic_charts.3d_plots",
    "title": "Magnetic Field 3D Visualization",
    "position": {"row": 0, "column": 1},
    "size": {"width": 600, "height": 500},
    "specific_config": {
      "vector_display": {
        "show_vectors": true,
        "vector_scale": 1000,
        "vector_density": 10,
        "color_by_magnitude": true
      },
      "coordinate_system": {
        "show_axes": true,
        "show_labels": true,
        "axes_color": "black",
        "background_color": "white"
      },
      "magnetic_components": {
        "show_x_component": true,
        "show_y_component": true,
        "show_z_component": true,
        "show_magnitude": true,
        "component_colors": {
          "x": "#ff0000",
          "y": "#00ff00",
          "z": "#0000ff",
          "magnitude": "#000000"
        }
      },
      "reference_field": {
        "show_earth_field": true,
        "earth_field_color": "#808080",
        "earth_field_opacity": 0.3
      },
      "animation": {
        "auto_rotate": false,
        "rotation_speed": 1.0,
        "show_trajectory": true,
        "trajectory_length": 100
      }
    }
  },
  "usgs_comparison_chart": {
    "chart_type": "comparison_charts.correlation",
    "title": "Local vs USGS Comparison",
    "position": {"row": 1, "column": 0, "colspan": 2},
    "size": {"width": 800, "height": 400},
    "specific_config": {
      "comparison_type": "correlation",
      "observatory": "BOU",
      "time_alignment": {
        "tolerance_minutes": 5,
        "interpolation_method": "linear"
      },
      "statistics": {
        "show_correlation_coeff": true,
        "show_rms_difference": true,
        "show_mean_difference": true,
        "show_confidence_interval": true,
        "confidence_level": 0.95
      },
      "visualization": {
        "show_perfect_correlation_line": true,
        "show_regression_line": true,
        "point_size": 3,
        "point_alpha": 0.6,
        "color_by_time": true
      }
    }
  }
}
```

#### Chart-Specific Configuration Examples

##### Temperature Chart Configuration Dialog
```python
def create_temperature_chart_config_tab(self, notebook):
    """Temperature-specific configuration options"""
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Temperature Settings")

    # Temperature unit selection
    ttk.Label(frame, text="Temperature Unit:").grid(row=0, column=0, sticky="w")
    self.temp_unit_var = tk.StringVar(value=self.chart_config.get('temperature_unit', 'celsius'))
    temp_unit_combo = ttk.Combobox(frame, textvariable=self.temp_unit_var,
                                  values=['celsius', 'fahrenheit', 'kelvin'])
    temp_unit_combo.grid(row=0, column=1, sticky="ew")

    # Trend line options
    self.show_trend_var = tk.BooleanVar(value=self.chart_config.get('show_trend_line', True))
    ttk.Checkbutton(frame, text="Show Trend Line",
                   variable=self.show_trend_var).grid(row=1, column=0, columnspan=2, sticky="w")

    # Alert thresholds
    ttk.Label(frame, text="Alert Thresholds:").grid(row=2, column=0, sticky="w")

    threshold_frame = ttk.LabelFrame(frame, text="Alerts")
    threshold_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)

    self.alert_enabled_var = tk.BooleanVar(value=self.chart_config.get('alert_thresholds', {}).get('enabled', True))
    ttk.Checkbutton(threshold_frame, text="Enable Alerts",
                   variable=self.alert_enabled_var).grid(row=0, column=0, columnspan=2)

    ttk.Label(threshold_frame, text="Low Threshold:").grid(row=1, column=0)
    self.low_threshold_var = tk.DoubleVar(value=self.chart_config.get('alert_thresholds', {}).get('low', -10.0))
    ttk.Entry(threshold_frame, textvariable=self.low_threshold_var, width=10).grid(row=1, column=1)

    ttk.Label(threshold_frame, text="High Threshold:").grid(row=2, column=0)
    self.high_threshold_var = tk.DoubleVar(value=self.chart_config.get('alert_thresholds', {}).get('high', 40.0))
    ttk.Entry(threshold_frame, textvariable=self.high_threshold_var, width=10).grid(row=2, column=1)
```

##### Magnetic 3D Chart Configuration Dialog
```python
def create_magnetic_3d_config_tab(self, notebook):
    """Magnetic 3D chart-specific configuration"""
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="3D Visualization")

    # Vector display options
    vector_frame = ttk.LabelFrame(frame, text="Vector Display")
    vector_frame.pack(fill="x", pady=5)

    self.show_vectors_var = tk.BooleanVar(value=self.chart_config.get('vector_display', {}).get('show_vectors', True))
    ttk.Checkbutton(vector_frame, text="Show Magnetic Vectors",
                   variable=self.show_vectors_var).pack(anchor="w")

    ttk.Label(vector_frame, text="Vector Scale:").pack(anchor="w")
    self.vector_scale_var = tk.IntVar(value=self.chart_config.get('vector_display', {}).get('vector_scale', 1000))
    scale_widget = tk.Scale(vector_frame, from_=100, to=10000,
                           variable=self.vector_scale_var, orient="horizontal")
    scale_widget.pack(fill="x")

    # Component display options
    component_frame = ttk.LabelFrame(frame, text="Magnetic Components")
    component_frame.pack(fill="x", pady=5)

    components = ['x', 'y', 'z', 'magnitude']
    self.component_vars = {}

    for component in components:
        var = tk.BooleanVar(value=self.chart_config.get('magnetic_components', {}).get(f'show_{component}_component', True))
        self.component_vars[component] = var
        ttk.Checkbutton(component_frame, text=f"Show {component.upper()} Component",
                       variable=var).pack(anchor="w")

    # Animation options
    animation_frame = ttk.LabelFrame(frame, text="Animation")
    animation_frame.pack(fill="x", pady=5)

    self.auto_rotate_var = tk.BooleanVar(value=self.chart_config.get('animation', {}).get('auto_rotate', False))
    ttk.Checkbutton(animation_frame, text="Auto Rotate View",
                   variable=self.auto_rotate_var).pack(anchor="w")

    self.show_trajectory_var = tk.BooleanVar(value=self.chart_config.get('animation', {}).get('show_trajectory', True))
    ttk.Checkbutton(animation_frame, text="Show Field Trajectory",
                   variable=self.show_trajectory_var).pack(anchor="w")
```

#### Configuration Manager Enhancement
```python
# utils/config_manager.py
class ConfigManager:
    def load_chart_instance_config(self, chart_id):
        """Load chart-specific configuration with inheritance"""
        # Load chart instance config
        instance_config = self._load_config("chart_instances.json").get(chart_id, {})

        # Load chart type config
        chart_type = instance_config.get('chart_type', '')
        type_config = self._get_chart_type_config(chart_type)

        # Load global chart config
        global_config = self._load_config("charts_config.json").get('general', {})

        # Merge configurations (instance overrides type overrides global)
        merged_config = {}
        merged_config.update(global_config)
        merged_config.update(type_config)
        merged_config.update(instance_config.get('specific_config', {}))

        return merged_config

    def save_chart_instance_config(self, chart_id, config):
        """Save chart-specific configuration"""
        chart_instances = self._load_config("chart_instances.json")

        if chart_id not in chart_instances:
            chart_instances[chart_id] = {
                "chart_type": "unknown",
                "title": chart_id,
                "specific_config": {}
            }

        chart_instances[chart_id]['specific_config'].update(config)
        self._save_config("chart_instances.json", chart_instances)

    def get_effective_config(self, chart_id):
        """Get the effective configuration after inheritance"""
        return self.load_chart_instance_config(chart_id)
```

#### Chart Header with Configuration Button
```python
# charts/base_chart.py
class BaseChart:
    def create_chart_header(self):
        """Create chart header with title and configuration button"""
        self.header_frame = tk.Frame(self.parent_container, bg="#f0f0f0", height=30)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        # Chart title
        title_label = tk.Label(
            self.header_frame,
            text=self.title,
            bg="#f0f0f0",
            font=("Arial", 10, "bold")
        )
        title_label.pack(side="left", padx=5, pady=5)

        # Configuration button
        self.create_config_button()

        # Undock button (if in docked mode)
        if not self.is_undocked:
            self.create_undock_button()

    def create_config_button(self):
        """Create configuration button for chart-specific settings"""
        config_btn = tk.Button(
            self.header_frame,
            text="⚙️",
            command=self.show_config_dialog,
            width=3,
            relief=tk.FLAT,
            bg="#f0f0f0",
            font=("Arial", 8)
        )
        config_btn.pack(side="right", padx=2, pady=2)

        # Tooltip
        self.create_tooltip(config_btn, "Configure chart settings")

    def apply_configuration(self, new_config):
        """Apply new configuration to chart"""
        self.config.update(new_config)

        # Save to persistent storage
        self.config_manager.save_chart_instance_config(self.chart_id, new_config)

        # Refresh chart with new settings
        self.refresh()

        # Notify other components if needed
        self.on_config_changed(new_config)
```

### Window State Persistence
- Save window positions, sizes, and docking states
- Restore on application startup
- Handle multi-monitor configurations
- Graceful handling of missing displays

## Benefits of Modular Architecture

### Development Benefits
1. **Separation of Concerns** - Each module has single responsibility
2. **Easy Testing** - Mock individual components independently
3. **Plugin Architecture** - Add new sensors/charts without core changes
4. **Maintainability** - Changes isolated to specific modules
5. **Reusability** - Components can be reused across different interfaces

### User Benefits
1. **Flexible Configuration** - Granular control over all aspects
2. **Customizable Layouts** - Charts arranged as needed
3. **Multi-Monitor Support** - Charts can span multiple displays
4. **Persistent Preferences** - Settings saved between sessions
5. **Modular Functionality** - Enable/disable features as needed

### System Benefits
1. **Scalability** - Easy to add new data sources and visualizations
2. **Performance** - Components can be optimized independently
3. **Configuration Management** - Centralized yet organized settings
4. **Backup/Restore** - Configuration can be easily backed up
5. **Version Control** - Configuration changes trackable

## Migration Strategy

### Phase 1: Configuration Extraction
- Create configuration files from hardcoded values
- Implement `ConfigManager` utility
- Update existing code to use configuration system

### Phase 2: Module Separation
- Extract sensor interfaces into `sensors/` module
- Create chart base classes in `charts/` module
- Implement data layer in `data/` module

### Phase 3: GUI Modernization
- Implement chart manager for undocking capability
- Create window state persistence
- Add context menus and user preferences

### Phase 4: Advanced Features
- Multi-monitor support
- Chart layout presets
- Configuration import/export
- Plugin system for custom sensors/charts

## Technical Considerations

### Performance
- Configuration caching to avoid repeated file reads
- Lazy loading of chart modules
- Efficient window state management
- Background data refresh for undocked windows

### Error Handling
- Graceful degradation for missing configuration files
- Validation of configuration values
- Recovery from corrupted window states
- Fallback to defaults when needed

### Security
- Input validation for all configuration values
- Safe file handling for configuration persistence
- Secure defaults for network settings
- Protection against configuration injection attacks

## Future Extensions

### Planned Features
1. **Plugin System** - Third-party sensors and charts
2. **Remote Configuration** - Network-based settings management
3. **Configuration Profiles** - Different setups for different use cases
4. **Chart Templates** - Predefined chart configurations
5. **Export/Import** - Configuration backup and sharing

### Integration Points
1. **Home Automation** - MQTT integration with other systems
2. **Data Analysis** - Export capabilities for external tools
3. **Alerting System** - Configurable thresholds and notifications
4. **Web Interface** - Browser-based remote monitoring
5. **Mobile Apps** - Smartphone/tablet interfaces

This architecture provides a solid foundation for the weather station project's continued evolution while maintaining the existing functionality and performance characteristics.