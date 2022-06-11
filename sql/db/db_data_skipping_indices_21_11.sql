select
	_shard_num,
	hostName() as host_name,
	database,
	table,
	name,
	type,
	expr,
	granularity,
	data_compressed_bytes,
	data_uncompressed_bytes,
	formatReadableSize(data_compressed_bytes) as pretty_compressed_bytes,
	marks
from clusterAllReplicas(_CLUSTER_NAME, system.data_skipping_indices)
order by name;