#!/bin/sh
set -eu

ch_diag_require_clickhouse_pid
printf 'Selected ClickHouse server for native port %s\n' "$CH_DIAG_DATABASE_PORT"
ps -ww -p "$CH_DIAG_CLICKHOUSE_PID" -o pid=,ppid=,user=,group=,lstart=,etime=,stat=,comm=,args=

ch_diag_frontier=$CH_DIAG_CLICKHOUSE_PID
ch_diag_depth=0
while [ -n "$ch_diag_frontier" ] && [ "$ch_diag_depth" -lt 8 ]; do
  ch_diag_next=""
  for ch_diag_parent in $ch_diag_frontier; do
    ch_diag_children=$(ps -e -o pid=,ppid= | awk -v parent="$ch_diag_parent" '$2 == parent {print $1}')
    for ch_diag_child in $ch_diag_children; do
      ps -ww -p "$ch_diag_child" -o pid=,ppid=,user=,group=,lstart=,etime=,stat=,comm=,args= || true
      ch_diag_next="$ch_diag_next $ch_diag_child"
    done
  done
  ch_diag_frontier=$ch_diag_next
  ch_diag_depth=$((ch_diag_depth + 1))
done
exit 0
