select
	_shard_num,
	hostName() as host_name,
	name,
	free_space as free_space,
	total_space as total_space,
	keep_free_space,
	type
from clusterAllReplicas({{cluster}}, system.disks)
order by _shard_num, host_name, name