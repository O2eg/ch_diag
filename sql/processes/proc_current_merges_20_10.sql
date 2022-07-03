SELECT
	_shard_num,
	hostName() as host_name,
	database,
	table,
	round(elapsed, 1) "elapsed",
	round(100 * progress, 1) "progress",
	is_mutation,
	partition_id,
	num_parts,
	merge_type,
	formatReadableSize(total_size_bytes_compressed) "total_size_compressed",
	formatReadableSize(bytes_read_uncompressed) "read_uncompressed",
	formatReadableSize(bytes_written_uncompressed) "written_uncompressed",
	columns_written,
	rows_read,
	rows_written,
	formatReadableSize(memory_usage) "memory_usage"
from clusterAllReplicas(_CLUSTER_NAME, system.merges)
order by _shard_num, host_name, database, table
limit 1000