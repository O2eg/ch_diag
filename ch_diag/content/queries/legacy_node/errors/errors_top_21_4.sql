-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	name,
	code,
	value,
	remote,
	last_error_message,
	last_error_time
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.errors)
order by _shard_num, host_name, value desc
limit 100;