select
	_shard_num,
	hostName() as host_name,
	name,
	value,
	changed
from clusterAllReplicas(_CLUSTER_NAME, system.settings)
where
	name like '%thread%' or
	name like '%pool%' or
	name like '%memo%' or
	name like '%sync%' or
	name like '%optimiz%'
order by _shard_num, host_name, name