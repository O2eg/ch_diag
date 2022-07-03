select
	_shard_num,
	hostName() as host_name,
	event,
	value,
	if(
		match(event, 'Bytes|Chars|MemoryCode|Memory|Buffers'),
		formatReadableSize(value),
		toString(value)
	) as pretty_value
from clusterAllReplicas(_CLUSTER_NAME, system.events)
order by value desc
limit 200;