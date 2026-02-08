#!/bin/bash

# Kill processes by pattern - works on both Debian and Alpine
# Uses SIGKILL (-9) to ensure immediate termination
kill_by_pattern() {
    local pattern="$1"
    pkill -9 -f "$pattern" 2>/dev/null || \
        ps aux | grep -v grep | grep "$pattern" | awk '{print $2}' | xargs -r kill -9 2>/dev/null
    return 0
}

# Kill bench-related processes (precise patterns to avoid killing vscode-server)
kill_by_pattern "node apps/frappe/socketio.js"
kill_by_pattern "node apps/frappe/realtime"
kill_by_pattern "bench start"
kill_by_pattern "frappe.utils.bench_helper"
kill_by_pattern "frappe serve"
kill_by_pattern "frappe worker"
kill_by_pattern "schedule"
kill_by_pattern "watch"
kill_by_pattern "pydevd.py"
