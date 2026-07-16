#!/bin/sh
set -eu

ch_diag_require_clickhouse_pid
printf 'PID: %s\nNative port: %s\n' "$CH_DIAG_CLICKHOUSE_PID" "$CH_DIAG_DATABASE_PORT"
printf '%s\n' 'Command line:'
tr '\000' ' ' < "/proc/$CH_DIAG_CLICKHOUSE_PID/cmdline"
printf '\n%s\n' 'Executable:'
ch_diag_clickhouse_executable || printf '%s\n' unavailable
printf '%s\n' 'Resource limits:'
sed -n '1,200p' "/proc/$CH_DIAG_CLICKHOUSE_PID/limits"
printf '%s\n' 'Security status:'
awk '/^(Name|Umask|Uid|Gid|NoNewPrivs|Seccomp|Cpus_allowed_list|Mems_allowed_list):/' \
  "/proc/$CH_DIAG_CLICKHOUSE_PID/status"
