select
	_shard_num,
	hostName() as host_name,
	event,
	value
from clusterAllReplicas({{cluster}}, system.events)
order by value desc
limit 200;