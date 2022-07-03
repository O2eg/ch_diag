select
	_shard_num,
	hostName() as host_name,
	database,
	table,
	name,
	type,
	expr,
	granularity
from clusterAllReplicas(_CLUSTER_NAME, system.data_skipping_indices)
order by name;