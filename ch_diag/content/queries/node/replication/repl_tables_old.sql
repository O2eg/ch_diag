-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
SELECT
    _shard_num,
    hostName() as host_name,
    database,
    table,
    absolute_delay,
    replica_path,
    is_leader,
    is_readonly,
    is_session_expired,
    future_parts,
    parts_to_check,
    queue_size,
    inserts_in_queue,
    merges_in_queue,
    log_max_index,
    log_pointer,
    total_replicas,
    active_replicas,
    zookeeper_exception
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.replicas)
ORDER BY absolute_delay DESC
LIMIT 5000