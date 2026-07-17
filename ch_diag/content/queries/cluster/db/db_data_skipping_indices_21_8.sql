select
	_shard_num,
	hostName() as host_name,
	database,
	table,
	name,
	type,
	expr,
	granularity
from clusterAllReplicas({{cluster}}, system.data_skipping_indices)
order by name;