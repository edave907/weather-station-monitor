# Weather Station Daemon - System Deployment Plan

## Overview

This document outlines the plan to deploy the Weather Station Monitor daemon as a system-level systemd service with automatic startup.

**Date**: 2025-11-16
**Current Status**: Development mode (running from `/home/david/projects/weatherstation`)
**Target Status**: Production system service (running from `/opt/weatherstation`)

---

## Deployment Architecture

### Directory Structure

```
/opt/weatherstation/                      # System installation directory
├── venv/                                 # Python virtual environment
│   ├── bin/
│   │   └── python                        # Python 3.12.6
│   └── lib/
│       └── python3.12/site-packages/     # Dependencies
├── src/                                  # Application source code
│   ├── main.py
│   ├── weather_daemon.py
│   ├── mqtt_subscriber.py
│   ├── database.py
│   ├── weather_gui.py
│   ├── weather_gui_tk.py
│   └── [other Python modules]
├── config/                               # Configuration files
│   └── weather_station_calibration.json  # Sensor calibration data
├── data/                                 # Runtime data
│   └── weather_data.db                   # SQLite database
├── logs/                                 # Log files
│   └── weather_daemon.log                # Daemon logs
├── run/                                  # Runtime files
│   └── weather_daemon.pid                # Process ID file
└── requirements.txt                      # Python dependencies

/etc/systemd/system/
└── weather-daemon.service                # Systemd service unit

/etc/logrotate.d/
└── weather-daemon                        # Log rotation config
```

### Service Configuration

**Service Type**: System service (not user service)
**User/Group**: `david:david` (runs as non-root user)
**Auto-start**: Enabled on boot
**Dependencies**: `network.target`, `mosquitto.service`
**Restart Policy**: Always restart on failure (10-second delay)

---

## Implementation Steps

### Phase 1: Pre-deployment Preparation

#### 1.1 Create System Directory Structure
```bash
# Create base directory (requires sudo)
sudo mkdir -p /opt/weatherstation/{src,config,data,logs,run}

# Set ownership to david user
sudo chown -R david:david /opt/weatherstation

# Set appropriate permissions
sudo chmod 755 /opt/weatherstation
sudo chmod 755 /opt/weatherstation/src
sudo chmod 775 /opt/weatherstation/{data,logs,run,config}
```

#### 1.2 Verify Prerequisites
```bash
# Check mosquitto service is available
systemctl status mosquitto

# Verify Python version
python3 --version  # Should be 3.12.6 or compatible

# Verify user david exists
id david
```

#### 1.3 Review Current Installation
```bash
# Current project size: ~553M (includes database and plots)
# Estimate deployment size: ~50-100M (excluding large data files)

# Identify files to exclude from deployment:
# - *.png, *.pdf (generated plots)
# - __pycache__/
# - .git/
# - weather_data.db (will be created fresh or migrated separately)
# - test files and examples
```

---

### Phase 2: Installation

#### 2.1 Create Python Virtual Environment
```bash
# Create venv in system location
cd /opt/weatherstation
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### 2.2 Copy Application Files
```bash
# Copy core application files
cp /home/david/projects/weatherstation/*.py /opt/weatherstation/src/

# Copy requirements
cp /home/david/projects/weatherstation/requirements.txt /opt/weatherstation/

# Copy calibration file
cp /home/david/projects/weatherstation/weather_station_calibration.json /opt/weatherstation/config/

# Do NOT copy:
# - Test files (test_*.py, *_validation_*.py)
# - Example files (example_*.py, demo_*.py)
# - Plot output directories
# - Development database
# - Documentation (keep in development repo)
```

**Files to Deploy** (Core Daemon):
- `main.py` - Entry point
- `weather_daemon.py` - Daemon implementation
- `mqtt_subscriber.py` - MQTT client
- `database.py` - Database interface
- `weather_gui.py` - GUI (for manual launches)
- `weather_gui_tk.py` - Tkinter GUI (for manual launches)
- `requirements.txt` - Dependencies

**Files to Deploy** (Optional - Advanced Features):
- `magnetic_flux_3d_plotter.py` - 3D visualization utility
- `magnetic_coordinate_calibrator.py` - Calibration utility
- `usgs_magnetic_importer.py` - USGS data integration

**Files to EXCLUDE**:
- `test_components.py`
- `run_gui*.py` (launcher scripts)
- `*_validation_*.py` (test scripts)
- `demo_*.py` (demonstration scripts)
- `example_*.py` (example scripts)
- Virtual observatory scripts (unless needed)

#### 2.3 Install Python Dependencies
```bash
# Activate venv
source /opt/weatherstation/venv/bin/activate

# Install dependencies
pip install -r /opt/weatherstation/requirements.txt

# Verify installation
pip list | grep -E 'paho-mqtt|matplotlib|numpy|tkcalendar'
```

#### 2.4 Create Systemd Service File
```bash
# Copy and modify service file
sudo cp /home/david/projects/weatherstation/systemd/weather-daemon.service \
        /etc/systemd/system/weather-daemon.service

# Edit paths in service file (see modified version below)
sudo nano /etc/systemd/system/weather-daemon.service
```

**Modified Service File** (`/etc/systemd/system/weather-daemon.service`):
```ini
[Unit]
Description=Weather Station Data Collector Daemon
Documentation=file:///opt/weatherstation/README.md
After=network.target mosquitto.service
Wants=mosquitto.service

[Service]
Type=simple
User=david
Group=david
WorkingDirectory=/opt/weatherstation/src
Environment=PATH=/opt/weatherstation/venv/bin:/usr/local/bin:/usr/bin
ExecStart=/opt/weatherstation/venv/bin/python main.py --daemon --silent \
          --db /opt/weatherstation/data/weather_data.db \
          --log /opt/weatherstation/logs/weather_daemon.log \
          --pid /opt/weatherstation/run/weather_daemon.pid

# Restart policy
Restart=always
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=300

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=weather-daemon

# Security hardening
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/weatherstation/data /opt/weatherstation/logs /opt/weatherstation/run

# Resource limits
MemoryLimit=500M
CPUQuota=50%

# Kill the daemon gracefully
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

**Key Changes from Development Version**:
- ✅ Updated `WorkingDirectory` to `/opt/weatherstation/src`
- ✅ Updated `Environment` PATH to system venv
- ✅ Updated `ExecStart` with explicit paths for `--db`, `--log`, `--pid`
- ✅ Added `--silent` flag for production (journal logging only)
- ✅ Added security hardening (`ProtectSystem`, `ProtectHome`, etc.)
- ✅ Added resource limits (`MemoryLimit`, `CPUQuota`)
- ✅ Added restart limits (`StartLimitBurst`, `StartLimitIntervalSec`)
- ✅ Increased `TimeoutStopSec` to 30 seconds
- ✅ Added `SyslogIdentifier` for easier log filtering
- ✅ Added `Documentation` directive

#### 2.5 Setup Log Rotation
```bash
# Copy logrotate configuration
sudo cp /home/david/projects/weatherstation/logrotate/weather-daemon \
        /etc/logrotate.d/weather-daemon

# Edit paths in logrotate config
sudo nano /etc/logrotate.d/weather-daemon
```

**Modified Logrotate Config** (`/etc/logrotate.d/weather-daemon`):
```
/opt/weatherstation/logs/weather_daemon.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 david david
    sharedscripts
    postrotate
        # Send USR1 signal to daemon to reopen log file
        if [ -f /opt/weatherstation/run/weather_daemon.pid ]; then
            kill -USR1 $(cat /opt/weatherstation/run/weather_daemon.pid) 2>/dev/null || true
        fi
    endscript
}
```

---

### Phase 3: Configuration

#### 3.1 Database Migration (Optional)
```bash
# Option A: Start fresh (recommended for clean deployment)
# Database will be created automatically on first run

# Option B: Migrate existing data
cp /home/david/projects/weatherstation/weather_data.db \
   /opt/weatherstation/data/weather_data.db
chown david:david /opt/weatherstation/data/weather_data.db
chmod 664 /opt/weatherstation/data/weather_data.db
```

#### 3.2 Verify Calibration Configuration
```bash
# Check calibration file exists
ls -l /opt/weatherstation/config/weather_station_calibration.json

# Verify permissions
chmod 664 /opt/weatherstation/config/weather_station_calibration.json
```

#### 3.3 MQTT Broker Configuration
```bash
# Ensure mosquitto is running
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# Verify MQTT topics are accessible
mosquitto_sub -v -t 'backacres/house/weatherstation/#' -C 1

# If authentication is required, configure in daemon
# (future enhancement: add --mqtt-user and --mqtt-password flags)
```

---

### Phase 4: Service Activation

#### 4.1 Reload Systemd Configuration
```bash
sudo systemctl daemon-reload
```

#### 4.2 Enable Service (Auto-start on Boot)
```bash
sudo systemctl enable weather-daemon.service
```

#### 4.3 Start Service
```bash
sudo systemctl start weather-daemon.service
```

#### 4.4 Verify Service Status
```bash
# Check service status
sudo systemctl status weather-daemon.service

# Check service is active
systemctl is-active weather-daemon.service

# Check service is enabled
systemctl is-enabled weather-daemon.service

# Check recent logs
sudo journalctl -u weather-daemon -n 50 --no-pager

# Follow logs in real-time
sudo journalctl -u weather-daemon -f
```

#### 4.5 Verify Data Collection
```bash
# Wait 1-2 minutes for data collection
sleep 120

# Check database has data
sqlite3 /opt/weatherstation/data/weather_data.db "SELECT COUNT(*) FROM weather_data;"
sqlite3 /opt/weatherstation/data/weather_data.db "SELECT COUNT(*) FROM magnetic_flux_data;"

# Check log file
tail -f /opt/weatherstation/logs/weather_daemon.log

# Check PID file
cat /opt/weatherstation/run/weather_daemon.pid
ps -p $(cat /opt/weatherstation/run/weather_daemon.pid)
```

---

### Phase 5: Testing

#### 5.1 Service Control Tests
```bash
# Test stop
sudo systemctl stop weather-daemon
systemctl is-active weather-daemon  # Should show "inactive"

# Test start
sudo systemctl start weather-daemon
systemctl is-active weather-daemon  # Should show "active"

# Test restart
sudo systemctl restart weather-daemon

# Test reload (log rotation)
sudo kill -USR1 $(cat /opt/weatherstation/run/weather_daemon.pid)

# Check logs after reload
tail /opt/weatherstation/logs/weather_daemon.log
```

#### 5.2 Failure Recovery Tests
```bash
# Test automatic restart on crash
# Kill the process ungracefully
sudo kill -9 $(cat /opt/weatherstation/run/weather_daemon.pid)

# Wait 10 seconds (restart delay)
sleep 15

# Verify service restarted
systemctl is-active weather-daemon
sudo journalctl -u weather-daemon -n 20 --no-pager
```

#### 5.3 Boot Test
```bash
# Reboot system
sudo reboot

# After reboot, verify service started automatically
systemctl is-active weather-daemon
sudo systemctl status weather-daemon
```

#### 5.4 Log Rotation Test
```bash
# Force log rotation
sudo logrotate -f /etc/logrotate.d/weather-daemon

# Verify old log was rotated
ls -lh /opt/weatherstation/logs/

# Verify daemon continues logging to new file
tail /opt/weatherstation/logs/weather_daemon.log
```

---

### Phase 6: GUI Access (Optional)

#### 6.1 GUI Launch Script
Since the daemon runs in background, users may want to launch the GUI separately:

```bash
# Create GUI launcher script
cat > /opt/weatherstation/launch-gui.sh <<'EOF'
#!/bin/bash
# Launch Weather Station GUI
cd /opt/weatherstation/src
source /opt/weatherstation/venv/bin/activate
python weather_gui_tk.py --db /opt/weatherstation/data/weather_data.db
EOF

chmod +x /opt/weatherstation/launch-gui.sh
```

#### 6.2 Desktop Shortcut (Optional)
```bash
# Create desktop entry for GUI
cat > ~/.local/share/applications/weather-station.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Weather Station Monitor
Comment=View weather station data and charts
Exec=/opt/weatherstation/launch-gui.sh
Icon=weather-clear
Terminal=false
Categories=Science;Education;
EOF

chmod +x ~/.local/share/applications/weather-station.desktop
```

---

## Service Management Commands

### Daily Operations

```bash
# View service status
sudo systemctl status weather-daemon

# View recent logs (last 100 lines)
sudo journalctl -u weather-daemon -n 100

# View logs with timestamps
sudo journalctl -u weather-daemon --since "1 hour ago"

# Follow logs in real-time
sudo journalctl -u weather-daemon -f

# Restart service
sudo systemctl restart weather-daemon

# Stop service
sudo systemctl stop weather-daemon

# Start service
sudo systemctl start weather-daemon

# View service configuration
systemctl cat weather-daemon

# Check service dependencies
systemctl list-dependencies weather-daemon
```

### Troubleshooting

```bash
# Check if mosquitto is running
systemctl status mosquitto

# Test MQTT connection manually
mosquitto_sub -v -t 'backacres/house/weatherstation/#'

# Check database permissions
ls -l /opt/weatherstation/data/weather_data.db

# Check log file permissions
ls -l /opt/weatherstation/logs/weather_daemon.log

# Verify Python environment
/opt/weatherstation/venv/bin/python --version
/opt/weatherstation/venv/bin/pip list

# Check disk space
df -h /opt/weatherstation

# View all systemd errors
sudo journalctl -p err -u weather-daemon

# Debug mode (stop service and run manually)
sudo systemctl stop weather-daemon
cd /opt/weatherstation/src
source /opt/weatherstation/venv/bin/activate
python main.py --daemon --verbose
```

---

## Rollback Plan

If deployment encounters issues, rollback to development mode:

### 1. Stop System Service
```bash
sudo systemctl stop weather-daemon
sudo systemctl disable weather-daemon
```

### 2. Resume Development Mode
```bash
cd /home/david/projects/weatherstation
source venv/bin/activate
python main.py --daemon
```

### 3. Remove System Installation (Optional)
```bash
# Remove service file
sudo rm /etc/systemd/system/weather-daemon.service
sudo systemctl daemon-reload

# Remove logrotate config
sudo rm /etc/logrotate.d/weather-daemon

# Remove installation directory (CAUTION: backup data first!)
sudo cp -r /opt/weatherstation/data ~/weatherstation-backup/
sudo rm -rf /opt/weatherstation
```

---

## Security Considerations

### File Permissions Summary

```
/opt/weatherstation/               755  david:david
/opt/weatherstation/src/           755  david:david
/opt/weatherstation/config/        775  david:david
/opt/weatherstation/data/          775  david:david
/opt/weatherstation/logs/          775  david:david
/opt/weatherstation/run/           775  david:david

weather_data.db                    664  david:david
weather_station_calibration.json   664  david:david
weather_daemon.log                 640  david:david
weather_daemon.pid                 644  david:david
```

### Systemd Security Features Enabled

- ✅ `PrivateTmp=true` - Isolated /tmp directory
- ✅ `NoNewPrivileges=true` - Prevents privilege escalation
- ✅ `ProtectSystem=strict` - Read-only system directories
- ✅ `ProtectHome=true` - No access to other user home directories
- ✅ `ReadWritePaths` - Explicit write permissions only to data/logs/run
- ✅ `MemoryLimit=500M` - Prevents memory exhaustion
- ✅ `CPUQuota=50%` - Prevents CPU hogging

### MQTT Security (Future Enhancement)

Current: Unauthenticated localhost connection
Recommended: Add username/password authentication if exposing beyond localhost

---

## Maintenance Schedule

### Daily (Automated)
- Log rotation (via logrotate)
- Service monitoring (via systemd)

### Weekly (Manual)
- Review logs for errors: `sudo journalctl -u weather-daemon --since "7 days ago" | grep -i error`
- Check database size: `du -h /opt/weatherstation/data/weather_data.db`
- Verify data collection: Check recent database entries

### Monthly (Manual)
- Review and archive old logs
- Database vacuum: `sqlite3 /opt/weatherstation/data/weather_data.db "VACUUM;"`
- Check disk space: `df -h /opt/weatherstation`
- Verify calibration accuracy

### Quarterly (Manual)
- Review and update Python dependencies
- Test backup/restore procedures
- Review systemd service configuration for optimization

---

## Success Criteria

Deployment is considered successful when:

- ✅ Service starts automatically on boot
- ✅ Service restarts automatically on failure
- ✅ Logs are written to `/opt/weatherstation/logs/weather_daemon.log`
- ✅ Logs are rotated daily and retained for 30 days
- ✅ Data is collected and stored in SQLite database
- ✅ Service status shows "active (running)"
- ✅ No errors in systemd journal
- ✅ MQTT connection is stable
- ✅ Database grows with new data
- ✅ GUI can connect to system database
- ✅ Service survives system reboot

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Service fails to start | High | Low | Test thoroughly before enabling; keep development version as fallback |
| Database corruption | High | Low | Regular backups; use SQLite WAL mode |
| Disk space exhaustion | Medium | Medium | Log rotation; database size monitoring |
| MQTT connection loss | Medium | Medium | Auto-reconnect logic already implemented |
| Permission issues | Low | Medium | Careful permission setup; run as david user |
| Python dependency issues | Medium | Low | Use virtual environment; pin versions |
| Log file growth | Low | High | Logrotate configured for 30-day retention |

---

## Post-Deployment Verification Checklist

- [ ] Service file copied to `/etc/systemd/system/`
- [ ] Systemd daemon reloaded
- [ ] Service enabled for auto-start
- [ ] Service started successfully
- [ ] Service status shows "active (running)"
- [ ] Logs appear in systemd journal
- [ ] Logs appear in `/opt/weatherstation/logs/weather_daemon.log`
- [ ] PID file created at `/opt/weatherstation/run/weather_daemon.pid`
- [ ] Database created at `/opt/weatherstation/data/weather_data.db`
- [ ] Data is being collected (check database after 2 minutes)
- [ ] Logrotate configuration installed
- [ ] Log rotation tested
- [ ] Service restart tested
- [ ] Service survives reboot
- [ ] GUI can access system database
- [ ] No errors in logs
- [ ] MQTT connection stable
- [ ] File permissions correct
- [ ] Development environment still functional (fallback)

---

## Estimated Timeline

- **Phase 1** (Pre-deployment): 15 minutes
- **Phase 2** (Installation): 30 minutes
- **Phase 3** (Configuration): 15 minutes
- **Phase 4** (Service Activation): 10 minutes
- **Phase 5** (Testing): 30 minutes
- **Phase 6** (GUI Access): 10 minutes

**Total Estimated Time**: ~2 hours (including testing and verification)

---

## Notes and Considerations

1. **Database Compatibility**: The SQLite database format is compatible between development and production installations. Users can copy the database file between locations.

2. **Calibration Files**: The `weather_station_calibration.json` file contains sensor calibration values that should be preserved during deployment.

3. **MQTT Topics**: The service assumes standard MQTT topics (`backacres/house/weatherstation/`). If these change, update the topics in the code or add configuration file support.

4. **Resource Usage**: Current service limits (500M RAM, 50% CPU) are conservative. Monitor actual usage and adjust if needed.

5. **Multiple Instances**: The current configuration runs a single instance. To run multiple instances (e.g., for different MQTT brokers), create templated service units.

6. **Python Version**: Deployment assumes Python 3.12.6. If system Python differs, specify explicit Python version in venv creation.

7. **Development Workflow**: After deployment, continue development in `/home/david/projects/weatherstation`. Deploy updates by copying modified files to `/opt/weatherstation/src/` and restarting the service.

---

## Appendix: Installation Script (Future Enhancement)

A deployment automation script (`install.sh`) could be created to automate these steps:

```bash
#!/bin/bash
# install.sh - Automated deployment script
# Usage: sudo ./install.sh

# This script would:
# 1. Create directory structure
# 2. Copy files
# 3. Create virtual environment
# 4. Install dependencies
# 5. Configure systemd
# 6. Configure logrotate
# 7. Enable and start service
# 8. Run verification tests

# Not implemented yet - current plan is manual deployment
```

---

**End of Deployment Plan**

**Next Steps**: Review this plan, make any necessary modifications, then execute deployment when approved.
