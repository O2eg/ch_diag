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
printf '%s\n' __CH_DIAG_PROCESS_THREADS__
awk '
  {
    line = $0
    opening = index(line, "(")
    closing = 0
    for (position = length(line); position > opening; position--) {
      if (substr(line, position, 1) == ")") {
        closing = position
        break
      }
    }
    if (opening < 2 || closing == 0) next
    count = split(substr(line, closing + 2), fields, " +")
    if (count < 20) next
    thread_id = substr(line, 1, opening - 1)
    thread_name = substr(line, opening + 1, closing - opening - 1)
    print thread_id "\t" fields[1] "\t" fields[20] "\t" fields[12] "\t" fields[13] "\t" thread_name
  }
' "/proc/$CH_DIAG_CLICKHOUSE_PID"/task/[0-9]*/stat 2>/dev/null || true
printf '%s\n' __CH_DIAG_PROCESS_THREAD_IO__
awk '
  FILENAME != previous_file {
    if (previous_file != "") print thread_id "\t" read_bytes "\t" write_bytes
    previous_file = FILENAME
    count = split(FILENAME, path, "/")
    thread_id = path[count - 1]
    read_bytes = 0
    write_bytes = 0
  }
  $1 == "read_bytes:" { read_bytes = $2 }
  $1 == "write_bytes:" { write_bytes = $2 }
  END {
    if (previous_file != "") print thread_id "\t" read_bytes "\t" write_bytes
  }
' "/proc/$CH_DIAG_CLICKHOUSE_PID"/task/[0-9]*/io 2>/dev/null || true
