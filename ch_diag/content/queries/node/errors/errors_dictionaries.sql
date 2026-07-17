-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	database,
	name,
	type,
	status,
	last_successful_update_time,
	loading_duration as loading_duration,
	last_exception
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.dictionaries)
WHERE status in ('FAILED', 'FAILED_AND_RELOADING')
order by _shard_num, host_name, database, name