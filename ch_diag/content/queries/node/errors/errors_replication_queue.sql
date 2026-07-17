-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	database,
    table,
    node_name,
    replica_name,
	source_replica,
	type,
	is_currently_executing,
	last_exception,
    last_attempt_time,
    num_postponed,
    postpone_reason
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.replication_queue)
where last_exception != '' or num_postponed > 0
order by _shard_num, host_name, database, table
