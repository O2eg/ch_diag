select
	_shard_num,
	hostName() as host_name,
	name,
	formatReadableSize(free_space) as free_space,
	formatReadableSize(total_space) as total_space,
	keep_free_space
from clusterAllReplicas(_CLUSTER_NAME, system.disks)
order by _shard_num, host_name, name