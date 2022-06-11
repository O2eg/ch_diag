select
	_shard_num,
	hostName() as host_name,
	name,
	value,
	changed
from clusterAllReplicas(_CLUSTER_NAME, system.merge_tree_settings)
where
	name like '%memo%' or
	name like '%sync%' or
	name like '%merge%' or
	name like '%granul%' or
	name like '%min%rows%' or
	name like '%min%part%' or
	name like '%max%part%'
order by _shard_num, host_name, name