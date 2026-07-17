SELECT
	_shard_num,
	hostName() as host_name,
	database,
	table,
	elapsed "elapsed",
	100 * progress "progress",
	is_mutation,
	partition_id,
	num_parts,
	total_size_bytes_compressed "total_size_compressed",
	bytes_read_uncompressed "read_uncompressed",
	bytes_written_uncompressed "written_uncompressed",
	columns_written,
	rows_read,
	rows_written,
	memory_usage "memory_usage"
from clusterAllReplicas({{cluster}}, system.merges)
order by _shard_num, host_name, database, table
limit 1000