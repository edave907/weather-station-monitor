# Weather Daemon Failsafe Implementation Plan

**Date**: 2025-11-16
**Objective**: Make the daemon mode fully failsafe with multiple layers of protection

---

## Current Vulnerabilities

### 1. **PID File Lock** (Weak Protection)
- Current: PID file written but not locked
- Issue: Multiple daemons can start simultaneously
- Risk: Database conflicts, data corruption

### 2. **Database Locking** (No Protection)
- Current: No database-level locking mechanism
- Issue: SQLite file locks insufficient for preventing concurrent writes
- Risk: "database is locked" errors, write failures

### 3. **No Mutual Exclusion**
- Current: No mechanism to prevent second instance
- Issue: User can accidentally start multiple daemons
- Risk: Conflicts, data loss, inconsistent state

### 4. **No Health Monitoring**
- Current: Basic MQTT reconnection only
- Issue: No watchdog for database health
- Risk: Silent failures, stuck processes

### 5. **Limited Error Recovery**
- Current: Basic exception handling
- Issue: Some errors cause daemon to exit
- Risk: Service downtime

---

## Failsafe Strategy

### Layer 1: PID File Locking (Prevents Multiple Instances)
### Layer 2: Database WAL Mode (Enables Concurrent Readers)
### Layer 3: Advisory File Locking (System-level Lock)
### Layer 4: Health Monitoring (Watchdog)
### Layer 5: Automatic Recovery (Error Handling)

---

## Implementation Plan

### Layer 1: PID File Locking

**Objective**: Prevent multiple daemon instances from starting

**Implementation**:
```python
import fcntl
import errno

class WeatherDaemon:
    def __init__(self, ...):
        ...
        self.pid_file_handle = None
        self.lock_file = None

    def acquire_exclusive_lock(self):
        """Acquire exclusive lock to prevent multiple instances."""
        try:
            # Open PID file for writing
            self.pid_file_handle = open(self.pid_file, 'w')

            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(self.pid_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write PID after acquiring lock
            self.pid_file_handle.write(str(os.getpid()) + '\n')
            self.pid_file_handle.flush()

            self.logger.info(f"Acquired exclusive lock on {self.pid_file}")
            return True

        except IOError as e:
            if e.errno in (errno.EACCES, errno.EAGAIN):
                # Lock already held by another process
                self.logger.error(f"Another instance is already running (PID file locked: {self.pid_file})")
                self.logger.error("Cannot start daemon - another instance is active")
                return False
            else:
                self.logger.error(f"Failed to acquire lock: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Unexpected error acquiring lock: {e}")
            return False

    def release_exclusive_lock(self):
        """Release the exclusive lock."""
        if self.pid_file_handle:
            try:
                fcntl.flock(self.pid_file_handle.fileno(), fcntl.LOCK_UN)
                self.pid_file_handle.close()
                self.logger.info("Released exclusive lock")
            except Exception as e:
                self.logger.warning(f"Failed to release lock: {e}")

    def start(self):
        """Start the daemon with exclusive lock."""
        # Acquire exclusive lock FIRST
        if not self.acquire_exclusive_lock():
            self.logger.error("Cannot start - another instance is already running")
            sys.exit(1)

        try:
            # ... existing start logic ...
        finally:
            # Always release lock on exit
            self.release_exclusive_lock()
```

**Benefits**:
- ✅ Prevents multiple daemon instances
- ✅ System-level lock (works across all processes)
- ✅ Automatic lock release on process death
- ✅ Non-blocking check (immediate failure if locked)

---

### Layer 2: Database WAL Mode

**Objective**: Enable concurrent readers while daemon writes

**Implementation**:
```python
class WeatherDatabase:
    def init_database(self) -> None:
        """Initialize database with WAL mode."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Enable WAL mode for concurrent access
            cursor.execute("PRAGMA journal_mode=WAL;")

            # Set synchronous mode for better performance
            cursor.execute("PRAGMA synchronous=NORMAL;")

            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys=ON;")

            # Set busy timeout (wait up to 5 seconds for lock)
            conn.execute("PRAGMA busy_timeout = 5000;")

            self.logger.info("Database initialized with WAL mode")

            # ... existing table creation ...
```

**Benefits**:
- ✅ Multiple readers can read while daemon writes
- ✅ No more "database is locked" for readers (GUI, plotters)
- ✅ Better concurrency
- ✅ Improved performance

**Trade-offs**:
- Creates -wal and -shm files (deleted on clean close)
- Requires SQLite 3.7.0+ (we have newer)

---

### Layer 3: Advisory File Locking

**Objective**: Additional database-level lock protection

**Implementation**:
```python
class WeatherDatabase:
    def __init__(self, db_path: str = "weather_data.db"):
        self.db_path = db_path
        self.lock_file_path = db_path + ".lock"
        self.lock_file_handle = None
        self.init_database()

    def acquire_database_lock(self):
        """Acquire advisory lock on database."""
        try:
            self.lock_file_handle = open(self.lock_file_path, 'w')
            fcntl.flock(self.lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file_handle.write(f"Locked by PID {os.getpid()}\n")
            self.lock_file_handle.flush()
            return True
        except IOError:
            return False

    def release_database_lock(self):
        """Release advisory lock on database."""
        if self.lock_file_handle:
            try:
                fcntl.flock(self.lock_file_handle.fileno(), fcntl.LOCK_UN)
                self.lock_file_handle.close()
                if os.path.exists(self.lock_file_path):
                    os.remove(self.lock_file_path)
            except Exception as e:
                pass
```

---

### Layer 4: Health Monitoring Watchdog

**Objective**: Detect and recover from failures

**Implementation**:
```python
class WeatherDaemon:
    def __init__(self, ...):
        ...
        self.last_successful_write = None
        self.write_failures = 0
        self.max_write_failures = 10
        self.database_health_ok = True

    def check_health(self):
        """Perform health checks."""
        issues = []

        # Check MQTT connection
        if not self.mqtt_subscriber.is_connected():
            issues.append("MQTT disconnected")

        # Check last successful write
        if self.last_successful_write:
            time_since_write = datetime.now() - self.last_successful_write
            if time_since_write.total_seconds() > 60:  # No writes for 1 minute
                issues.append(f"No successful writes for {time_since_write.total_seconds():.0f} seconds")

        # Check write failure rate
        if self.write_failures >= self.max_write_failures:
            issues.append(f"Too many write failures ({self.write_failures})")
            self.database_health_ok = False

        # Check database accessibility
        try:
            test_conn = sqlite3.connect(self.db_path, timeout=1)
            test_conn.execute("SELECT 1")
            test_conn.close()
        except Exception as e:
            issues.append(f"Database not accessible: {e}")
            self.database_health_ok = False

        if issues:
            self.logger.warning(f"Health check issues: {', '.join(issues)}")

        return len(issues) == 0

    def on_write_success(self):
        """Track successful database write."""
        self.last_successful_write = datetime.now()
        self.write_failures = 0

    def on_write_failure(self, error):
        """Track database write failure."""
        self.write_failures += 1
        self.logger.error(f"Database write failed ({self.write_failures}/{self.max_write_failures}): {error}")

        if self.write_failures >= self.max_write_failures:
            self.logger.critical("Maximum write failures reached - entering degraded mode")
            # Could trigger alert, email, etc.
```

---

### Layer 5: Automatic Error Recovery

**Objective**: Recover from transient errors without exiting

**Implementation**:
```python
class WeatherDatabase:
    def insert_weather_data(self, data: Dict, retry_count: int = 3) -> bool:
        """Insert weather data with retry logic."""
        for attempt in range(retry_count):
            try:
                with sqlite3.connect(self.db_path, timeout=10) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO weather_data
                        (timestamp, sample_interval, temperature, humidity, pressure,
                         irradiance, wind_direction, rain_gauge_count, anemometer_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data.get('utc'),
                        data.get('sampleinterval'),
                        data.get('temperature'),
                        data.get('humidity'),
                        data.get('pressure'),
                        data.get('irradiance'),
                        data.get('winddirectionsensor'),
                        data.get('raingaugecount'),
                        data.get('anemometercount')
                    ))
                    conn.commit()
                    return True  # Success

            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < retry_count - 1:
                    # Database locked - wait and retry
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise  # Re-raise if max retries exceeded
            except Exception as e:
                raise  # Re-raise unexpected errors

        return False  # Failed after all retries
```

---

## Enhanced MQTT Subscriber

**Add graceful error handling**:
```python
class WeatherMQTTSubscriber:
    def _on_message(self, client, userdata, msg):
        """Callback with enhanced error handling."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)

            self.logger.info(f"Received data from {topic}: {data}")

            # Store data with error tracking
            success = False
            if "weathermeters" in topic:
                success = self.database.insert_weather_data(data)
                if success:
                    self.logger.info("Stored weather data in database")
            elif "magneticfluxsensor" in topic:
                success = self.database.insert_magnetic_flux_data(data)
                if success:
                    self.logger.info("Stored magnetic flux data in database")

            # Notify daemon of write status
            if self.data_callback:
                self.data_callback(topic, data, success)

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from {msg.topic}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message from {msg.topic}: {e}")
            # Don't crash - log and continue
```

---

## Complete Failsafe Daemon

**Putting it all together**:
```python
class WeatherDaemon:
    def start(self):
        """Start the daemon with all failsafe mechanisms."""
        self.logger.info("Starting Weather Station Daemon (Failsafe Mode)")

        # Layer 1: Acquire exclusive lock
        if not self.acquire_exclusive_lock():
            self.logger.error("FAILSAFE: Cannot start - another instance is already running")
            sys.exit(1)

        try:
            # Layer 2: Initialize database with WAL mode
            self.database.init_database()

            # Layer 3: Acquire database lock
            if not self.database.acquire_database_lock():
                self.logger.error("FAILSAFE: Cannot acquire database lock")
                sys.exit(1)

            # Start MQTT subscriber
            self.mqtt_subscriber.start()
            self.running = True
            self.start_time = datetime.now()

            self.logger.info("Daemon started successfully (all failsafes active)")

            # Main daemon loop with health monitoring
            stats_counter = 0
            health_counter = 0

            while self.running:
                time.sleep(1)

                # Log statistics every 5 minutes
                stats_counter += 1
                if stats_counter >= 300:
                    self.log_statistics()
                    stats_counter = 0

                # Layer 4: Health check every 60 seconds
                health_counter += 1
                if health_counter >= 60:
                    health_ok = self.check_health()
                    if not health_ok:
                        self.logger.warning("Health check failed - attempting recovery")
                    health_counter = 0

                # MQTT reconnection if needed
                if not self.mqtt_subscriber.is_connected():
                    self.logger.warning("MQTT connection lost, attempting to reconnect...")
                    try:
                        self.mqtt_subscriber.start()
                    except Exception as e:
                        self.logger.error(f"Reconnection failed: {e}")
                        time.sleep(10)

        except KeyboardInterrupt:
            self.logger.info("Daemon interrupted by user")
        except Exception as e:
            self.logger.error(f"Daemon error: {e}")
            raise
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up all resources."""
        self.logger.info("Cleaning up daemon resources...")

        if self.running:
            self.running = False

        # Stop MQTT subscriber
        if self.mqtt_subscriber:
            self.mqtt_subscriber.stop()

        # Release database lock
        if self.database:
            self.database.release_database_lock()

        # Release exclusive lock
        self.release_exclusive_lock()

        # Log final statistics
        self.log_statistics()

        self.logger.info("Daemon stopped and cleaned up")
```

---

## Testing the Failsafe System

### Test 1: Multiple Instance Prevention
```bash
# Terminal 1
cd ~/projects/weatherstation
source venv/bin/activate
python main.py --daemon --db /tmp/test.db

# Terminal 2 (should fail)
python main.py --daemon --db /tmp/test.db
# Expected: "Cannot start - another instance is already running"
```

### Test 2: Concurrent Reader Access
```bash
# Daemon running
python weather_gui_tk.py --db /deepsink1/weatherstation/data/weather_data.db
# Expected: Works without "database is locked" errors
```

### Test 3: Health Monitoring
```bash
# Stop MQTT broker
sudo systemctl stop mosquitto

# Check daemon logs
tail -f /opt/weatherstation/logs/weather_daemon.log
# Expected: Health check warnings, auto-reconnect attempts

# Restart MQTT broker
sudo systemctl start mosquitto
# Expected: Daemon reconnects automatically
```

### Test 4: Error Recovery
```bash
# Simulate database lock by opening in exclusive mode
sqlite3 /deepsink1/weatherstation/data/weather_data.db
# In sqlite3 prompt: BEGIN EXCLUSIVE;

# Watch daemon logs - should retry and eventually succeed
tail -f /opt/weatherstation/logs/weather_daemon.log
```

---

## Deployment Steps

1. **Backup current code**
2. **Update weather_daemon.py** with failsafe mechanisms
3. **Update database.py** with WAL mode and retry logic
4. **Update mqtt_subscriber.py** with error handling
5. **Test in development** with test database
6. **Deploy to production** via systemd service restart
7. **Monitor for 24 hours** to verify stability

---

## Benefits Summary

| Feature | Before | After | Benefit |
|---------|--------|-------|---------|
| **Multiple Instances** | Possible | Prevented | No conflicts |
| **Concurrent Reads** | Locks | Allowed | GUI always works |
| **Write Errors** | Fail | Retry | Better reliability |
| **Health Monitoring** | None | Active | Early problem detection |
| **MQTT Failures** | Basic retry | Enhanced | Better recovery |
| **Database Locks** | None | Advisory | Protection |
| **Error Recovery** | Limited | Comprehensive | Less downtime |

---

## Monitoring and Alerts

### Add to daemon for production monitoring:
```python
def send_alert(self, message, severity="WARNING"):
    """Send alert for critical issues."""
    # Could implement:
    # - Email notifications
    # - Slack/Discord webhooks
    # - SMS alerts
    # - System notifications
    self.logger.log(logging.WARNING if severity == "WARNING" else logging.CRITICAL,
                    f"ALERT [{severity}]: {message}")
```

---

## Recommended Next Steps

1. **Implement Layer 1** (PID locking) - **Highest Priority**
2. **Implement Layer 2** (WAL mode) - **High Priority**
3. **Implement Layer 5** (Error recovery) - **Medium Priority**
4. **Implement Layer 4** (Health monitoring) - **Medium Priority**
5. **Implement Layer 3** (Database locking) - **Lower Priority** (optional with WAL)

---

**Status**: Ready for implementation
**Risk Level**: Low (all changes are additive, no breaking changes)
**Testing Required**: Yes (comprehensive testing plan provided)

---

*End of Daemon Failsafe Plan*
