#!/bin/sh
set -eu

ch_diag_require_clickhouse_pid

ch_diag_config=$(
  tr '\000' '\n' < "/proc/$CH_DIAG_CLICKHOUSE_PID/cmdline" 2>/dev/null |
    awk '
      previous == "--config-file" { print; exit }
      /^--config-file=/ { sub(/^--config-file=/, ""); print; exit }
      { previous = $0 }
    '
)
[ -n "$ch_diag_config" ] || ch_diag_config=/etc/clickhouse-server/config.xml
ch_diag_config_dir=$(dirname "$ch_diag_config")

printf 'PID\tNative port\tConfig file\n'
printf '%s\t%s\t%s\n\n' "$CH_DIAG_CLICKHOUSE_PID" "$CH_DIAG_DATABASE_PORT" "$ch_diag_config"
printf 'Mode\tOctal\tOwner\tGroup\tPath\tAdvisory\n'
{
  printf '%s\n' \
    "$ch_diag_config" \
    "$ch_diag_config_dir" \
    "$ch_diag_config_dir/config.d" \
    "$ch_diag_config_dir/users.xml" \
    "$ch_diag_config_dir/users.d" \
    /var/lib/clickhouse \
    /var/log/clickhouse-server
} | awk '!seen[$0]++' | while IFS= read -r ch_diag_path; do
  [ -e "$ch_diag_path" ] || continue
  ch_diag_mode=$(stat -Lc '%a' "$ch_diag_path" 2>/dev/null || printf unknown)
  ch_diag_advisory=-
  case "$ch_diag_mode" in
    *[2367]) ch_diag_advisory=world-writable ;;
  esac
  stat -Lc '%A\t%a\t%U\t%G\t%n' "$ch_diag_path" 2>/dev/null |
    awk -v advisory="$ch_diag_advisory" '{print $0 "\t" advisory}'
done
