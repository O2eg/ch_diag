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
	marks
from clusterAllReplicas({{cluster}}, system.data_skipping_indices)
order by name;