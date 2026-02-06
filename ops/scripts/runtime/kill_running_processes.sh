#!/bin/bash

pkill -f "pydevd.py"
pkill -f "bench start"
pkill -f "frappe worker"
pkill -f "frappe.utils.bench_helper"
pkill -f "watch"
pkill -f "schedule"
pkill -f "frappe serve"
pkill -f "node apps/frappe/socketio.js"
sleep 1

