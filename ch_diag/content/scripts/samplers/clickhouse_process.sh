#!/bin/sh
set -eu

ch_diag_require_clickhouse_pid
printf '%s\n' __CH_DIAG_PROCESS_PID__ "$CH_DIAG_CLICKHOUSE_PID"
printf '%s\n' __CH_DIAG_PROCESS_HZ__
getconf CLK_TCK
printf '%s\n' __CH_DIAG_PROCESS_PAGE_SIZE__
getconf PAGESIZE
printf '%s\n' __CH_DIAG_PROCESS_STAT__
cat "/proc/$CH_DIAG_CLICKHOUSE_PID/stat"
printf '%s\n' __CH_DIAG_PROCESS_IO__
if ! cat "/proc/$CH_DIAG_CLICKHOUSE_PID/io" 2>/dev/null; then
  printf '%s\n' unavailable
fi
