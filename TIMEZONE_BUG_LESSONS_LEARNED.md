# Timezone Bug - Lessons Learned

**Date:** 2025-12-25
**Affected Component:** Weather Station Monitor GUI (`weather_gui_tk.py`)
**Severity:** Medium - Charts displayed incorrect times (9-hour offset)

## Problem Summary

The Weather Station Monitor GUI was displaying chart timestamps incorrectly, showing times approximately 9 hours ahead of actual local time (Alaska, UTC-9).

## Root Cause Analysis

### Data Flow

```
Sensor (UTC) --> MQTT --> Database (UTC) --> GUI Query --> Chart Display
     |                        |                  |              |
  Unix timestamp         created_at          Local times    Naive datetime
  (unambiguous)          (UTC, no TZ marker)  vs UTC query   (assumed local)
```

### Issues Identified

#### 1. Inconsistent Timestamp Sources
The GUI used `created_at` (index 8) instead of the Unix `timestamp` (index 0):
```python
# Before (buggy)
timestamp_str = row[8]  # created_at: "2025-12-25 22:05:26" (UTC)
timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
```
- `created_at` is UTC but has no timezone marker
- `.replace('Z', '+00:00')` had no effect (no 'Z' present)
- Result: naive datetime treated as local time by matplotlib

#### 2. Query Time Mismatch
Quick range queries used local time against UTC database values:
```python
# Before (buggy)
end_time = datetime.now()      # Local time (1:00 PM Alaska)
start_time = end_time - delta  # Local time
# Query: WHERE created_at BETWEEN '2025-12-25 12:00' AND '2025-12-25 13:00'
# But created_at contains: '2025-12-25 21:00' (UTC) - no match!
```

#### 3. Magnetic Flux Data
Same issue - parsing `created_at` without UTC conversion.

## Fixes Applied

### 1. Weather Data Timestamps (line 1018-1019)
```python
# After (fixed) - Use Unix timestamp, auto-converts to local
timestamp = datetime.fromtimestamp(row[0])
```

### 2. Query Time Range (lines 437-452)
```python
# After (fixed) - Query in UTC to match database
end_time = datetime.now(timezone.utc).replace(tzinfo=None)
start_time = end_time - time_delta
```

### 3. Magnetic Flux Timestamps (lines 517-519)
```python
# After (fixed) - Parse as UTC, convert to local
utc_time = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
timestamp = utc_time.astimezone().replace(tzinfo=None)
```

### 4. "Last Updated" Display (lines 897-900)
```python
# After (fixed) - Parse as UTC, convert to local
utc_time = datetime.fromisoformat(summary['last_updated']).replace(tzinfo=timezone.utc)
local_time = utc_time.astimezone().replace(tzinfo=None)
```

## Recommendations

### 1. Prefer Unix Timestamps
Unix timestamps are unambiguous (always UTC seconds since epoch). Use them as the primary time source:
```python
# Good - unambiguous
datetime.fromtimestamp(unix_ts)  # Automatically converts to local

# Risky - requires knowing the source timezone
datetime.fromisoformat(date_string)
```

### 2. Document Database Timezone Convention
Add to `CLAUDE.md` or schema documentation:
```markdown
## Database Time Conventions
- `timestamp` column: Unix epoch (UTC seconds)
- `created_at` column: SQLite CURRENT_TIMESTAMP (UTC, no TZ marker)
- All times stored in UTC; convert to local only for display
```

### 3. Use Timezone-Aware Datetimes
When working with timezones, use aware datetimes throughout:
```python
from datetime import datetime, timezone

# Aware datetime - explicit about timezone
now_utc = datetime.now(timezone.utc)
now_local = datetime.now().astimezone()

# Convert between zones explicitly
local_time = utc_time.astimezone()  # To local
utc_time = local_time.astimezone(timezone.utc)  # To UTC
```

### 4. Establish Clear Boundaries
Define where timezone conversions happen:
- **Database layer:** Always UTC
- **Business logic:** UTC preferred
- **Display layer:** Convert to local only at final rendering

### 5. Test with Non-UTC Timezones
Always test datetime handling in a timezone far from UTC. Alaska (UTC-9) exposed this bug; UTC or nearby timezones might have masked it.

### 6. Add Timezone Unit Tests
```python
def test_chart_times_are_local():
    """Verify chart displays local time, not UTC."""
    # Create test data with known UTC timestamp
    # Verify displayed time matches local conversion
    pass

def test_query_range_matches_utc_data():
    """Verify quick range queries return correct data."""
    # Insert data with known UTC created_at
    # Query with quick range
    # Verify returned data matches expected window
    pass
```

## Key Takeaways

1. **SQLite CURRENT_TIMESTAMP is UTC** - Don't assume it's local time
2. **Naive datetimes are dangerous** - They carry no timezone info and assumptions cause bugs
3. **Matplotlib treats naive datetimes as local** - This can mask or expose issues depending on context
4. **Query and display timezones must be consistent** - UTC for storage/queries, local for display
5. **Unix timestamps avoid ambiguity** - Prefer them over datetime strings when available

## Files Modified

| File | Changes |
|------|---------|
| `weather_gui_tk.py` | Added `timezone` import; fixed 4 timestamp conversion locations |

## Verification

After fixes, the GUI correctly displays:
- Chart X-axis in local time
- "Last Updated" in local time
- Quick range queries return the expected time window
- Custom range queries work correctly
