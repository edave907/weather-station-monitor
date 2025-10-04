# Contributing to Weather Station Monitor

Thank you for your interest in contributing to the Weather Station Monitor project! This document provides guidelines for contributing.

## Ways to Contribute

### 🐛 Bug Reports
- Use the GitHub Issues tab
- Include your operating system and Python version
- Provide steps to reproduce the issue
- Include relevant log files or error messages

### 💡 Feature Requests
- Check existing issues to avoid duplicates
- Describe the use case and expected behavior
- Consider NIST SP 330 compliance for new measurements

### 🔧 Code Contributions
- Fork the repository
- Create a feature branch: `git checkout -b feature-name`
- Follow the existing code style
- Test your changes thoroughly
- Submit a pull request

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/weather-station-monitor.git
   cd weather-station-monitor
   ```

2. **Set up virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Install system dependencies** (for GTK GUI):
   ```bash
   sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
   ```

4. **Test the application**:
   ```bash
   python test_components.py
   python weather_gui_tk.py  # Test Tkinter GUI
   ```

## Code Standards

### Python Style
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings for classes and methods
- Keep functions focused and small

### NIST SP 330 Compliance
- All new sensor measurements must use SI units
- Include proper unit conversions for display
- Document calibration formulas in comments
- Reference NIST SP 330 in calibration help text

### Database Schema
- Maintain backward compatibility
- Add migration scripts for schema changes
- Use proper SQLite data types
- Include indexes for performance

## Testing

### Component Testing
```bash
python test_components.py
```

### Manual Testing Checklist
- [ ] GUI starts without errors
- [ ] All chart types display correctly
- [ ] Calibration window opens and saves values
- [ ] MQTT connection works (if broker available)
- [ ] Database operations succeed
- [ ] Daemon mode starts and stops cleanly

## Documentation

### Code Documentation
- Add docstrings to new functions and classes
- Include type hints where appropriate
- Comment complex algorithms and calibration formulas

### User Documentation
- Update README.md for new features
- Add usage examples
- Include troubleshooting steps for common issues

## Sensor Support

### Adding New Sensors
1. Add calibration parameters to `default_calibration_values`
2. Create calibration UI section in `open_calibration_window()`
3. Update `apply_calibration()` method
4. Add chart configuration in `refresh_charts()`
5. Follow SI units standard (NIST SP 330)
6. Update documentation

### Sensor Calibration Guidelines
- Use SI base units for internal calculations
- Provide user-friendly display units
- Include helpful calibration text
- Validate input ranges
- Save to persistent calibration file

## Git Workflow

1. **Create feature branch**:
   ```bash
   git checkout -b feature/new-sensor-support
   ```

2. **Make commits with clear messages**:
   ```bash
   git commit -m "Add support for UV index sensor

   - Add UV index calibration parameters
   - Create UV chart visualization
   - Follow NIST SP 330 for W/m² measurements
   - Include sensor documentation"
   ```

3. **Push and create pull request**:
   ```bash
   git push origin feature/new-sensor-support
   ```

## Community Guidelines

- Be respectful and constructive
- Focus on technical improvements
- Help newcomers get started
- Share knowledge about weather station hardware
- Respect the NIST SP 330 standards for measurements

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open a GitHub Issue for technical questions
- Check existing documentation in README.md and CLAUDE.md
- Review the codebase for implementation examples

Thank you for helping make weather station monitoring better! 🌡️📊