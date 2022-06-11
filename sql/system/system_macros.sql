select
	_shard_num,
	hostName() as host_name,
	macro,
	substitution
from clusterAllReplicas(_CLUSTER_NAME, system.macros)
order by _shard_num, host_name, macro