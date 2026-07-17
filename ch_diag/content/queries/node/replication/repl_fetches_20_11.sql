-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
SELECT
	_shard_num,
	hostName() as host_name,
	database,
	table,
	elapsed as elapsed,
	100 * progress as progress,
	partition_id,
	result_part_name,
	result_part_path,
	total_size_bytes_compressed,
	bytes_read_compressed,
	source_replica_path,
	source_replica_hostname,
	source_replica_port,
	interserver_scheme,
	to_detached,
	thread_id
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.replicated_fetches)
order by elapsed desc
limit 1000