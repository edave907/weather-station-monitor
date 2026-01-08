# Weather Station Database Relocation Plan

**Date**: 2025-11-16
**Objective**: Move database files from `/opt/weatherstation/data/` to `/deepsink1/weatherstation/data/`

---

## Current Status

### Current Database Location
- **Path**: `/opt/weatherstation/data/weather_data.db`
- **Size**: 36 KB
- **Records**: 94 weather records, 94 magnetic flux records
- **Owner**: `david:david`
- **Permissions**: `644 (rw-r--r--)`

### Target Location
- **Path**: `/deepsink1/weatherstation/data/`
- **Filesystem**: `/dev/sdd1` (7.3T total, 5.8T available)
- **Reason**: Large storage capacity for long-term data collection

---

## Relocation Plan

### Step 1: Stop the Service
Stop the weather-daemon service to ensure database integrity during the move.

```bash
sudo systemctl stop weather-daemon
```

**Verification**:
```bash
systemctl is-active weather-daemon  # Should show "inactive"
```

### Step 2: Create Target Directory Structure
Create the new directory structure in `/deepsink1/`.

```bash
# Create directory
sudo mkdir -p /deepsink1/weatherstation/data

# Set ownership to david
sudo chown -R david:david /deepsink1/weatherstation

# Set permissions
sudo chmod 755 /deepsink1/weatherstation
sudo chmod 775 /deepsink1/weatherstation/data
```

**Verification**:
```bash
ls -la /deepsink1/weatherstation/
```

### Step 3: Move Database File
Move the database file to the new location.

```bash
# Move database file
mv /opt/weatherstation/data/weather_data.db /deepsink1/weatherstation/data/

# Verify ownership and permissions
ls -lh /deepsink1/weatherstation/data/weather_data.db
```

**Verification**:
```bash
# Check old location is empty (except any backup files)
ls -la /opt/weatherstation/data/

# Check new location has database
ls -lh /deepsink1/weatherstation/data/

# Test database integrity
sqlite3 /deepsink1/weatherstation/data/weather_data.db "PRAGMA integrity_check;"
sqlite3 /deepsink1/weatherstation/data/weather_data.db "SELECT COUNT(*) FROM weather_data;"
```

### Step 4: Update Systemd Service File
Update the service file to use the new database location.

**Current ExecStart**:
```
ExecStart=/usr/local/bin/python3.12 /opt/weatherstation/src/main.py --daemon --silent --db /opt/weatherstation/data/weather_data.db --log /opt/weatherstation/logs/weather_daemon.log --pid /opt/weatherstation/run/weather_daemon.pid
```

**New ExecStart**:
```
ExecStart=/usr/local/bin/python3.12 /opt/weatherstation/src/main.py --daemon --silent --db /deepsink1/weatherstation/data/weather_data.db --log /opt/weatherstation/logs/weather_daemon.log --pid /opt/weatherstation/run/weather_daemon.pid
```

**Implementation**:
```bash
# Edit service file (will be done via automated script)
# Update ReadWritePaths to include /deepsink1/weatherstation/data

# Reload systemd
sudo systemctl daemon-reload
```

### Step 5: Update Service Security Settings
Update the `ReadWritePaths` directive to include the new database location.

**Current ReadWritePaths**:
```
ReadWritePaths=/opt/weatherstation/data /opt/weatherstation/logs /opt/weatherstation/run /opt/weatherstation/config
```

**New ReadWritePaths**:
```
ReadWritePaths=/deepsink1/weatherstation/data /opt/weatherstation/logs /opt/weatherstation/run /opt/weatherstation/config
```

### Step 6: Create Symlink (Optional)
Optionally create a symlink at the old location pointing to the new location for convenience.

```bash
# Create symlink from old location to new location
ln -s /deepsink1/weatherstation/data/weather_data.db /opt/weatherstation/data/weather_data.db
```

**Note**: This is optional and mainly for convenience if any scripts reference the old path.

### Step 7: Start Service with New Configuration
Start the service with the updated configuration.

```bash
sudo systemctl start weather-daemon
```

**Verification**:
```bash
# Check service status
systemctl status weather-daemon --no-pager

# Wait 30 seconds for data collection
sleep 30

# Verify new data is being written
sqlite3 /deepsink1/weatherstation/data/weather_data.db "SELECT COUNT(*) FROM weather_data;"

# Check log file for any errors
tail -20 /opt/weatherstation/logs/weather_daemon.log

# Verify database is growing
watch -n 5 'ls -lh /deepsink1/weatherstation/data/weather_data.db'
```

### Step 8: Update GUI Launch Scripts
Update any GUI launch scripts to use the new database location.

```bash
# Update launch script (if exists)
# Change --db parameter from /opt/weatherstation/data/weather_data.db
# to /deepsink1/weatherstation/data/weather_data.db
```

---

## Updated File Structure

### After Relocation

```
/deepsink1/weatherstation/
└── data/
    └── weather_data.db              # Primary database (moved here)

/opt/weatherstation/
├── src/                             # Application code (unchanged)
├── venv/                            # Python environment (unchanged)
├── config/                          # Configuration (unchanged)
├── logs/                            # Log files (unchanged)
├── run/                             # PID file (unchanged)
└── data/                            # Now empty or contains symlink (optional)
```

---

## Service Configuration Changes

### Updated Service File

**Location**: `/etc/systemd/system/weather-daemon.service`

**Changes**:
1. `ExecStart` - Update `--db` parameter path
2. `ReadWritePaths` - Add `/deepsink1/weatherstation/data`

**Full updated service file** (`systemd/weather-daemon-production.service`):
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
Environment="PATH=/opt/weatherstation/venv/bin:/usr/local/bin:/usr/bin"
Environment="PYTHONPATH=/opt/weatherstation/venv/lib/python3.12/site-packages"
ExecStart=/usr/local/bin/python3.12 /opt/weatherstation/src/main.py --daemon --silent --db /deepsink1/weatherstation/data/weather_data.db --log /opt/weatherstation/logs/weather_daemon.log --pid /opt/weatherstation/run/weather_daemon.pid

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
ReadWritePaths=/deepsink1/weatherstation/data /opt/weatherstation/logs /opt/weatherstation/run /opt/weatherstation/config

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

---

## Rollback Plan

If issues occur, rollback to the original configuration:

### Step 1: Stop Service
```bash
sudo systemctl stop weather-daemon
```

### Step 2: Move Database Back
```bash
mv /deepsink1/weatherstation/data/weather_data.db /opt/weatherstation/data/
```

### Step 3: Restore Original Service File
```bash
# Restore from backup or git
sudo cp /home/david/projects/weatherstation/systemd/weather-daemon-production.service.backup /etc/systemd/system/weather-daemon.service
sudo systemctl daemon-reload
```

### Step 4: Restart Service
```bash
sudo systemctl start weather-daemon
```

---

## Verification Checklist

After relocation, verify:

- [ ] Service is running: `systemctl is-active weather-daemon`
- [ ] Database exists at new location: `ls -lh /deepsink1/weatherstation/data/weather_data.db`
- [ ] Database is readable: `sqlite3 /deepsink1/weatherstation/data/weather_data.db "SELECT COUNT(*) FROM weather_data;"`
- [ ] Database integrity: `sqlite3 /deepsink1/weatherstation/data/weather_data.db "PRAGMA integrity_check;"`
- [ ] New data is being collected (record count increasing)
- [ ] No errors in logs: `tail -50 /opt/weatherstation/logs/weather_daemon.log`
- [ ] No errors in systemd journal: `sudo journalctl -u weather-daemon -n 50`
- [ ] File permissions correct: `ls -lh /deepsink1/weatherstation/data/`
- [ ] Disk space sufficient: `df -h /deepsink1`

---

## Benefits of Relocation

### Storage Capacity
- **Current**: `/opt` is on system disk (limited space)
- **New**: `/deepsink1` has 5.8T available (ample for years of data)

### Data Organization
- Separates application code from data storage
- Allows independent backup strategies
- Better suited for long-term data retention

### Performance
- Dedicated storage device for database I/O
- No impact on system disk usage

---

## Backup Strategy Update

After relocation, update backup procedures:

### Database Backup Location
```bash
# Backup database to same filesystem for efficiency
sqlite3 /deepsink1/weatherstation/data/weather_data.db \
  ".backup /deepsink1/weatherstation/data/weather_data_backup_$(date +%Y%m%d).db"

# Weekly backups
0 2 * * 0 sqlite3 /deepsink1/weatherstation/data/weather_data.db \
  ".backup /deepsink1/weatherstation/backups/weather_data_$(date +\%Y\%m\%d).db"
```

---

## Additional Considerations

### GUI Access
When launching the GUI manually, use the new database path:

```bash
cd /opt/weatherstation/src
source /opt/weatherstation/venv/bin/activate
python weather_gui_tk.py --db /deepsink1/weatherstation/data/weather_data.db
```

### Development Environment
The development environment at `/home/david/projects/weatherstation/` remains unchanged.
For development, use the development database or specify the production database path.

### Monitoring
After relocation, monitor:
- Database growth rate
- Disk space on `/deepsink1`
- Service performance
- No permission errors in logs

---

## Estimated Downtime

**Total Estimated Downtime**: ~2-3 minutes

- Stop service: 10 seconds
- Move database: 5 seconds (small file)
- Update service: 30 seconds
- Reload and start: 10 seconds
- Verification: 60-90 seconds

**Data Loss**: None (service stopped during migration)

---

## Timeline

1. **Preparation**: Review this plan, backup current database (5 minutes)
2. **Execution**: Follow steps 1-7 (5 minutes)
3. **Verification**: Confirm operation (5 minutes)
4. **Monitoring**: Watch for 15-30 minutes to ensure stability

**Total Time**: ~20-30 minutes

---

## Notes

- Database file is currently small (36 KB) - move is very quick
- `/deepsink1` is already used by user `david`, so permissions should be straightforward
- Service will be down for ~2-3 minutes during the move
- All existing data (94 records) will be preserved
- Development environment remains unchanged at `/home/david/projects/weatherstation/`

---

**Ready to Execute**: Once you approve this plan, I will execute the relocation steps.

---

*End of Database Relocation Plan*
