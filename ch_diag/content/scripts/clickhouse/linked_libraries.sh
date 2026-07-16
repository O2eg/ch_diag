#!/bin/sh
set -eu

ch_diag_require_clickhouse_pid
ch_diag_executable=$(ch_diag_clickhouse_executable || true)
if [ -z "$ch_diag_executable" ] || [ ! -r "$ch_diag_executable" ]; then
  printf '%s\n' "cannot resolve the ClickHouse executable for PID $CH_DIAG_CLICKHOUSE_PID" >&2
  exit 3
fi
if ! command -v ldd >/dev/null 2>&1; then
  printf '%s\n' "ldd is not installed on the ClickHouse host" >&2
  exit 3
fi
printf 'PID: %s\nExecutable: %s\nNative port: %s\n' \
  "$CH_DIAG_CLICKHOUSE_PID" "$ch_diag_executable" "$CH_DIAG_DATABASE_PORT"
if ! ldd "$ch_diag_executable"; then
  printf '%s\n' 'ldd could not enumerate libraries; the executable may be statically linked' >&2
fi
