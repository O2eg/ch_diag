select
	_shard_num,
	hostName() as host_name,
	name,
	code,
	value
from clusterAllReplicas({{cluster}}, system.errors)
order by _shard_num, host_name, value desc
limit 100;
