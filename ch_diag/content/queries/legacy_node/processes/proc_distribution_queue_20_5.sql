-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	database,
	table,
	data_compressed_bytes,
	is_blocked,
	error_count,
	last_exception
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.distribution_queue)
order by _shard_num, host_name, database, table
limit 1000