# ClickHouse Configuration And Data Path Permissions

This item records ownership and permissions for the configuration selected by
the connected ClickHouse server process and for conventional data/log paths.

The process is mapped from the native port used by `ch_diag`; the collector
does not select an arbitrary ClickHouse instance when several servers run on
the same host. A `world-writable` advisory should be reviewed against the
host's deployment and access model.

The check is read-only. Missing conventional paths are omitted because custom
storage and logging locations may be configured elsewhere.
