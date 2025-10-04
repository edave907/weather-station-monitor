#!/bin/bash
# Test script for logrotate functionality

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_LOG="test_daemon.log"
TEST_PID="test_daemon.pid"

echo "Testing logrotate functionality..."

# Create a test daemon instance
echo "Starting test daemon..."
python main.py --daemon --silent --log "$TEST_LOG" --pid "$TEST_PID" &
TEST_DAEMON_PID=$!

# Wait for daemon to start and create some log entries
sleep 10

# Check if log file was created and has content
if [ -f "$TEST_LOG" ] && [ -s "$TEST_LOG" ]; then
    echo "✓ Log file created with content"
    echo "Log file size: $(du -h "$TEST_LOG" | cut -f1)"
    echo "Log entries: $(wc -l "$TEST_LOG" | cut -d' ' -f1)"
else
    echo "✗ Log file not created or empty"
    kill $TEST_DAEMON_PID 2>/dev/null || true
    exit 1
fi

# Test log rotation signal
echo "Testing USR1 signal for log rotation..."
if [ -f "$TEST_PID" ]; then
    DAEMON_PID=$(cat "$TEST_PID")
    echo "Sending USR1 signal to PID $DAEMON_PID"

    # Rename current log to simulate rotation
    mv "$TEST_LOG" "${TEST_LOG}.1"

    # Send USR1 signal
    kill -USR1 "$DAEMON_PID"

    # Wait a moment for log reopening
    sleep 5

    # Check if new log file was created
    if [ -f "$TEST_LOG" ] && [ -s "$TEST_LOG" ]; then
        echo "✓ Log file reopened successfully after rotation signal"
        grep "Log file reopened successfully" "$TEST_LOG" > /dev/null && echo "✓ Found log reopen confirmation"
    else
        echo "✗ Log file not reopened after rotation signal"
    fi
else
    echo "✗ PID file not found"
fi

# Clean up
echo "Cleaning up..."
kill $TEST_DAEMON_PID 2>/dev/null || true
sleep 2

# Remove test files
rm -f "$TEST_LOG" "${TEST_LOG}.1" "$TEST_PID"

echo "✓ Logrotate test completed successfully"