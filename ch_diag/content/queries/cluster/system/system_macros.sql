select
	_shard_num,
	hostName() as host_name,
	macro,
	substitution
from clusterAllReplicas({{cluster}}, system.macros)
order by _shard_num, host_name, macro