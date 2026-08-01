#!/bin/sh
set -eu

ch_diag_thread_mode=${1:-discover}
ch_diag_max_threads=${2:-2000}
ch_diag_requested_threads=${3:-}
ch_diag_discovered_hint=${4:-0}
case "$ch_diag_thread_mode" in
  process|discover|selected) ;;
  *) printf '%s\n' "invalid ClickHouse thread sampler mode" >&2; exit 2 ;;
esac
case "$ch_diag_max_threads" in
  ''|*[!0-9]*|0) printf '%s\n' "invalid ClickHouse thread sampler limit" >&2; exit 2 ;;
esac
case "$ch_diag_discovered_hint" in
  ''|*[!0-9]*) ch_diag_discovered_hint=0 ;;
esac

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

ch_diag_thread_rows=''
ch_diag_discovered_threads=0
ch_diag_selected_threads=0
if [ "$ch_diag_thread_mode" = discover ]; then
  ch_diag_all_thread_rows=$(
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
        cpu_ticks = fields[12] + fields[13]
        print cpu_ticks "\t" thread_id "\t" fields[1] "\t" fields[20] "\t" fields[12] "\t" fields[13] "\t" thread_name
      }
    ' "/proc/$CH_DIAG_CLICKHOUSE_PID"/task/[0-9]*/stat 2>/dev/null || true
  )
  ch_diag_discovered_threads=$(printf '%s\n' "$ch_diag_all_thread_rows" | awk 'NF { count++ } END { print count + 0 }')
  ch_diag_tab=$(printf '\t')
  ch_diag_thread_rows=$(
    printf '%s\n' "$ch_diag_all_thread_rows" \
      | sort -t "$ch_diag_tab" -k1,1nr -k2,2n \
      | sed -n "1,${ch_diag_max_threads}p" \
      | cut -f2-
  )
  ch_diag_selected_threads=$(printf '%s\n' "$ch_diag_thread_rows" | awk 'NF { count++ } END { print count + 0 }')
elif [ "$ch_diag_thread_mode" = selected ]; then
  ch_diag_discovered_threads=$ch_diag_discovered_hint
  ch_diag_stat_paths=''
  for ch_diag_tid in $(printf '%s' "$ch_diag_requested_threads" | tr ',' ' '); do
    case "$ch_diag_tid" in
      ''|*[!0-9]*) continue ;;
    esac
    ch_diag_selected_threads=$((ch_diag_selected_threads + 1))
    ch_diag_stat_path="/proc/$CH_DIAG_CLICKHOUSE_PID/task/$ch_diag_tid/stat"
    if [ -r "$ch_diag_stat_path" ]; then
      ch_diag_stat_paths="$ch_diag_stat_paths $ch_diag_stat_path"
    fi
  done
  if [ -n "$ch_diag_stat_paths" ]; then
    ch_diag_thread_rows=$(
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
      ' $ch_diag_stat_paths 2>/dev/null || true
    )
  fi
fi

ch_diag_captured_threads=$(printf '%s\n' "$ch_diag_thread_rows" | awk 'NF { count++ } END { print count + 0 }')
ch_diag_io_paths=''
for ch_diag_tid in $(printf '%s\n' "$ch_diag_thread_rows" | awk -F '\t' 'NF { print $1 }'); do
  ch_diag_io_path="/proc/$CH_DIAG_CLICKHOUSE_PID/task/$ch_diag_tid/io"
  if [ -r "$ch_diag_io_path" ]; then
    ch_diag_io_paths="$ch_diag_io_paths $ch_diag_io_path"
  fi
done
ch_diag_thread_io=''
if [ -n "$ch_diag_io_paths" ]; then
  ch_diag_thread_io=$(
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
    ' $ch_diag_io_paths 2>/dev/null || true
  )
fi
ch_diag_io_captured_threads=$(printf '%s\n' "$ch_diag_thread_io" | awk 'NF { count++ } END { print count + 0 }')

printf '%s\n' __CH_DIAG_PROCESS_DISCOVERED_THREADS__ "$ch_diag_discovered_threads"
printf '%s\n' __CH_DIAG_PROCESS_SELECTED_THREADS__ "$ch_diag_selected_threads"
printf '%s\n' __CH_DIAG_PROCESS_CAPTURED_THREADS__ "$ch_diag_captured_threads"
printf '%s\n' __CH_DIAG_PROCESS_IO_CAPTURED_THREADS__ "$ch_diag_io_captured_threads"
printf '%s\n' __CH_DIAG_PROCESS_THREADS__
printf '%s\n' "$ch_diag_thread_rows"
printf '%s\n' __CH_DIAG_PROCESS_THREAD_IO__
printf '%s\n' "$ch_diag_thread_io"
