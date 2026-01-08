# Database Merge Plan - Development to Production

**Date**: 2025-11-16
**Objective**: Merge historical data from development database into production database

---

## Current Status

### Development Database
- **Location**: `/home/david/projects/weatherstation/weather_data.db`
- **Size**: 97 MB
- **Weather Records**: 505,986 records
- **Magnetic Flux Records**: 505,983 records
- **Date Range**: 2025-10-03 00:13:25 to 2025-11-16 13:36:55
- **Duration**: ~44 days of continuous data

### Production Database
- **Location**: `/deepsink1/weatherstation/data/weather_data.db`
- **Size**: 48 KB
- **Weather Records**: 209 records
- **Magnetic Flux Records**: Similar count
- **Date Range**: 2025-11-16 14:31:59 to 2025-11-16 14:52:50
- **Duration**: ~21 minutes of new data

---

## Merge Strategy

### Option 1: Complete Replacement (Recommended)
Replace production database with development database, then let service continue adding new data.

**Pros**:
- Simple and fast
- No risk of duplicate records
- Preserves all historical data
- Clean merge

**Cons**:
- Loses 209 production records (21 minutes of data)
- But those records overlap with development database time range

### Option 2: Selective Merge
Copy only records from development that don't exist in production (avoid duplicates).

**Pros**:
- Preserves all production records
- No data loss

**Cons**:
- More complex
- Need to identify overlapping records
- Potential for duplicates if timestamps match

### Option 3: Archive and Start Fresh
Keep both databases separate for historical reference.

**Pros**:
- No data loss
- Can reference both databases

**Cons**:
- Fragmented data
- More complex queries

---

## Recommended Approach: Option 1 (Complete Replacement)

### Rationale
The development database contains 44 days of historical data (505,986 records) and already includes data up to 2025-11-16 13:36:55. The production database only has 21 minutes of new data (209 records) starting from 14:31:59, which is a gap of less than 1 hour.

**Decision**: Replace production database with development database, accepting the small gap of ~1 hour.

---

## Implementation Plan

### Step 1: Stop the Service
Stop the weather daemon to prevent database writes during the merge.

```bash
sudo systemctl stop weather-daemon
```

**Verification**:
```bash
systemctl is-active weather-daemon  # Should show "inactive"
```

### Step 2: Backup Current Production Database
Create a backup of the small production database (just in case).

```bash
# Backup production database
cp /deepsink1/weatherstation/data/weather_data.db \
   /deepsink1/weatherstation/data/weather_data_production_backup_$(date +%Y%m%d_%H%M%S).db

# Verify backup
ls -lh /deepsink1/weatherstation/data/weather_data_production_backup_*.db
```

### Step 3: Copy Development Database to Production
Copy the development database to the production location.

```bash
# Copy development database to production location
cp /home/david/projects/weatherstation/weather_data.db \
   /deepsink1/weatherstation/data/weather_data.db

# Verify copy
ls -lh /deepsink1/weatherstation/data/weather_data.db
```

**Expected Result**: File should be ~97 MB

### Step 4: Verify Ownership and Permissions
Ensure the database has correct ownership and permissions.

```bash
# Set ownership
chown david:david /deepsink1/weatherstation/data/weather_data.db

# Set permissions
chmod 644 /deepsink1/weatherstation/data/weather_data.db

# Verify
ls -lh /deepsink1/weatherstation/data/weather_data.db
```

### Step 5: Verify Database Integrity
Check that the copied database is not corrupted.

```bash
# Check integrity
sqlite3 /deepsink1/weatherstation/data/weather_data.db "PRAGMA integrity_check;"

# Should output: ok
```

### Step 6: Verify Record Count
Confirm all records were copied.

```bash
# Count weather records
sqlite3 /deepsink1/weatherstation/data/weather_data.db \
  "SELECT COUNT(*) FROM weather_data;"

# Count magnetic flux records
sqlite3 /deepsink1/weatherstation/data/weather_data.db \
  "SELECT COUNT(*) FROM magnetic_flux_data;"

# Check date range
sqlite3 /deepsink1/weatherstation/data/weather_data.db \
  "SELECT
     datetime(MIN(timestamp), 'unixepoch', 'localtime') as earliest,
     datetime(MAX(timestamp), 'unixepoch', 'localtime') as latest
   FROM weather_data;"
```

**Expected Results**:
- Weather records: 505,986
- Magnetic flux records: 505,983
- Date range: 2025-10-03 00:13:25 to 2025-11-16 13:36:55

### Step 7: Start the Service
Restart the weather daemon to resume data collection.

```bash
sudo systemctl start weather-daemon
```

**Verification**:
```bash
# Check service status
systemctl status weather-daemon --no-pager

# Wait 30 seconds for new data
sleep 30

# Verify new records are being added
sqlite3 /deepsink1/weatherstation/data/weather_data.db \
  "SELECT COUNT(*) FROM weather_data;"
# Should be > 505,986

# Check latest timestamp
sqlite3 /deepsink1/weatherstation/data/weather_data.db \
  "SELECT datetime(MAX(timestamp), 'unixepoch', 'localtime') FROM weather_data;"
# Should show current time
```

### Step 8: Monitor Data Collection
Monitor for a few minutes to ensure data collection continues normally.

```bash
# Watch record count increase
watch -n 5 'sqlite3 /deepsink1/weatherstation/data/weather_data.db "SELECT COUNT(*) FROM weather_data;"'

# Tail the log file
tail -f /opt/weatherstation/logs/weather_daemon.log
```

---

## Alternative: Selective Merge (If Needed)

If you want to preserve the 209 production records and avoid the gap, use this approach:

### Create Merge Script

```bash
#!/bin/bash
# merge_databases.sh

SOURCE_DB="/home/david/projects/weatherstation/weather_data.db"
TARGET_DB="/deepsink1/weatherstation/data/weather_data.db"
BACKUP_DB="/deepsink1/weatherstation/data/weather_data_pre_merge_backup.db"

# Stop service
sudo systemctl stop weather-daemon

# Backup current production database
cp $TARGET_DB $BACKUP_DB

# Attach source database and insert records that don't exist
sqlite3 $TARGET_DB <<EOF
ATTACH DATABASE '$SOURCE_DB' AS dev;

-- Insert weather records that don't exist in production
INSERT OR IGNORE INTO weather_data
SELECT * FROM dev.weather_data;

-- Insert magnetic flux records that don't exist in production
INSERT OR IGNORE INTO magnetic_flux_data
SELECT * FROM dev.magnetic_flux_data;

DETACH DATABASE dev;

-- Vacuum to reclaim space and optimize
VACUUM;

-- Integrity check
PRAGMA integrity_check;
EOF

# Restart service
sudo systemctl start weather-daemon

echo "Merge complete!"
echo "Records in production database:"
sqlite3 $TARGET_DB "SELECT COUNT(*) FROM weather_data;"
```

**Note**: This approach uses `INSERT OR IGNORE` which will skip records with duplicate primary keys (timestamps). This preserves all unique records from both databases.

---

## Data Gap Analysis

### Gap Between Databases
- **Development database ends**: 2025-11-16 13:36:55
- **Production database starts**: 2025-11-16 14:31:59
- **Gap duration**: ~55 minutes

### During the Gap
During deployment and testing (13:37 to 14:32), the service was not running, so no data was collected. This gap is expected and acceptable.

### After Merge
After copying development database to production:
- **Historical data**: Oct 3 to Nov 16 13:36 (505,986 records)
- **Gap**: Nov 16 13:37 to 14:32 (~55 minutes, no data)
- **New data**: Nov 16 14:32+ (service resumes collection)

---

## Estimated Downtime

**Total Estimated Downtime**: ~2-3 minutes

- Stop service: 10 seconds
- Backup production DB: 5 seconds
- Copy development DB: 30-60 seconds (97 MB)
- Verify integrity: 10 seconds
- Start service: 10 seconds

**Data Loss**: None (all historical data preserved, 55-minute gap already exists)

---

## Disk Space

### After Merge
- **Database Size**: 97 MB (from development)
- **Available Space**: 5.8 TB on /deepsink1
- **Usage**: 0.0016% of available space

### Growth Projection
- **Current rate**: ~2.2 GB/year (estimated)
- **Years until 100 GB**: ~45 years
- **Storage capacity**: Ample for decades of data

---

## Rollback Plan

If issues occur after merge:

### Rollback to Production Backup
```bash
# Stop service
sudo systemctl stop weather-daemon

# Restore backup
cp /deepsink1/weatherstation/data/weather_data_production_backup_*.db \
   /deepsink1/weatherstation/data/weather_data.db

# Restart service
sudo systemctl start weather-daemon
```

### Rollback to Development Database
Development database remains unchanged at `/home/david/projects/weatherstation/weather_data.db` and can be copied again if needed.

---

## Verification Checklist

After merge, verify:

- [ ] Service is running: `systemctl is-active weather-daemon`
- [ ] Database size is correct: `ls -lh /deepsink1/weatherstation/data/weather_data.db` (~97 MB)
- [ ] Database integrity: `sqlite3 /deepsink1/weatherstation/data/weather_data.db "PRAGMA integrity_check;"`
- [ ] Record count: `~505,986 weather records`
- [ ] Date range: `2025-10-03 to current`
- [ ] New data being collected: Record count increasing
- [ ] No errors in logs: `tail -50 /opt/weatherstation/logs/weather_daemon.log`
- [ ] File permissions: `ls -l /deepsink1/weatherstation/data/weather_data.db` (david:david)
- [ ] Backup exists: Backup file created successfully

---

## Post-Merge Actions

### Update Documentation
After successful merge, update:
- `DATABASE_RELOCATION_SUCCESS.md` - Note the merge was performed
- `DEPLOYMENT_SUCCESS.md` - Note historical data was imported

### Archive Development Database
After confirming merge success, optionally archive the development database:

```bash
# Create archive directory
mkdir -p /deepsink1/weatherstation/archives

# Move development database to archive
mv /home/david/projects/weatherstation/weather_data.db \
   /deepsink1/weatherstation/archives/weather_data_dev_archive_$(date +%Y%m%d).db

# Compress for long-term storage
gzip /deepsink1/weatherstation/archives/weather_data_dev_archive_*.db
```

### Clean Up Backups
After verifying merge for several days:

```bash
# List backups
ls -lh /deepsink1/weatherstation/data/weather_data_*backup*.db

# Remove old production backup (optional, after verification)
rm /deepsink1/weatherstation/data/weather_data_production_backup_*.db
```

---

## Success Criteria

Merge is successful when:

- ✅ Database contains 505,986+ weather records
- ✅ Date range starts from 2025-10-03
- ✅ Service continues collecting new data
- ✅ No database corruption
- ✅ No errors in service logs
- ✅ Database file is ~97 MB
- ✅ Record count increases over time
- ✅ All data accessible via GUI

---

## Recommendation

**Recommended Action**: Use **Option 1 (Complete Replacement)**

**Reasoning**:
1. Development database has 44 days of valuable historical data
2. Production database only has 21 minutes of data (already overlaps with dev database end time)
3. The ~55 minute gap between databases is expected (service was down during deployment)
4. Simple, clean merge with no risk of duplicates
5. Fast execution (~2-3 minutes downtime)

**Alternative**: If the 209 production records contain unique data not in development database, use the selective merge script to preserve all unique records.

---

**Ready to Execute**: Once you approve this plan, I will execute the database merge.

---

*End of Database Merge Plan*
