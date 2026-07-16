# Shared POSIX helpers for selecting the ClickHouse server bound to the connected port.

ch_diag_clickhouse_pid_from_socket() {
  ch_diag_port=$1
  ch_diag_hex_port=$(printf '%04X' "$ch_diag_port" 2>/dev/null) || return 1
  ch_diag_inodes=$(
    awk -v port="$ch_diag_hex_port" '
      $4 == "0A" {
        split($2, address, ":")
        if (toupper(address[2]) == port) print $10
      }
    ' /proc/net/tcp /proc/net/tcp6 2>/dev/null
  )
  [ -n "$ch_diag_inodes" ] || return 1
  for ch_diag_proc in /proc/[0-9]*; do
    [ -d "$ch_diag_proc/fd" ] || continue
    for ch_diag_fd in "$ch_diag_proc"/fd/*; do
      ch_diag_link=$(readlink "$ch_diag_fd" 2>/dev/null || true)
      case "$ch_diag_link" in
        socket:\[*\])
          ch_diag_inode=${ch_diag_link#socket:[}
          ch_diag_inode=${ch_diag_inode%]}
          for ch_diag_expected in $ch_diag_inodes; do
            if [ "$ch_diag_inode" = "$ch_diag_expected" ]; then
              basename "$ch_diag_proc"
              return 0
            fi
          done
          ;;
      esac
    done
  done
  return 1
}

ch_diag_clickhouse_pid() {
  ch_diag_port=${1:-}
  case "$ch_diag_port" in
    ''|*[!0-9]*) return 2 ;;
  esac
  if ch_diag_selected=$(ch_diag_clickhouse_pid_from_socket "$ch_diag_port"); then
    printf '%s\n' "$ch_diag_selected"
    return 0
  fi

  ch_diag_all=""
  ch_diag_matching=""
  for ch_diag_proc in /proc/[0-9]*; do
    [ -r "$ch_diag_proc/cmdline" ] || continue
    ch_diag_cmd=$(tr '\000' ' ' < "$ch_diag_proc/cmdline" 2>/dev/null || true)
    case "$ch_diag_cmd" in
      *clickhouse-server*|*clickhouse\ server*) ;;
      *) continue ;;
    esac
    ch_diag_pid=$(basename "$ch_diag_proc")
    ch_diag_all="$ch_diag_all $ch_diag_pid"
    case " $ch_diag_cmd " in
      *" --tcp_port=$ch_diag_port "*|*" --tcp_port $ch_diag_port "*)
        ch_diag_matching="$ch_diag_matching $ch_diag_pid"
        ;;
    esac
  done

  set -- $ch_diag_matching
  if [ "$#" -eq 1 ]; then
    printf '%s\n' "$1"
    return 0
  fi
  set -- $ch_diag_all
  if [ "$#" -eq 1 ]; then
    printf '%s\n' "$1"
    return 0
  fi
  return 3
}

ch_diag_require_clickhouse_pid() {
  ch_diag_status=0
  CH_DIAG_CLICKHOUSE_PID=$(ch_diag_clickhouse_pid "$CH_DIAG_DATABASE_PORT") || ch_diag_status=$?
  if [ "$ch_diag_status" -ne 0 ]; then
    if [ "$ch_diag_status" -eq 3 ]; then
      printf '%s\n' "multiple ClickHouse server processes found; port $CH_DIAG_DATABASE_PORT cannot be mapped safely" >&2
    else
      printf '%s\n' "ClickHouse server process for port $CH_DIAG_DATABASE_PORT was not found" >&2
    fi
    exit 3
  fi
  export CH_DIAG_CLICKHOUSE_PID
}

ch_diag_clickhouse_executable() {
  ch_diag_executable=$(readlink -f "/proc/$CH_DIAG_CLICKHOUSE_PID/exe" 2>/dev/null || true)
  if [ -n "$ch_diag_executable" ] && [ -r "$ch_diag_executable" ]; then
    printf '%s\n' "$ch_diag_executable"
    return 0
  fi
  ch_diag_command=$(tr '\000' '\n' < "/proc/$CH_DIAG_CLICKHOUSE_PID/cmdline" 2>/dev/null | sed -n '1p')
  ch_diag_command_name=$(basename "$ch_diag_command" 2>/dev/null || true)
  case "$ch_diag_command_name" in
    clickhouse|clickhouse-server)
      command -v "$ch_diag_command_name" 2>/dev/null
      return $?
      ;;
  esac
  return 1
}
