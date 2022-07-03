select
	_shard_num,
	hostName() as host_name,
	event,
	value,
	if(
		match(event, 'Bytes|Chars|MemoryCode|Memory|Buffers'),
		formatReadableSize(value),
		if (
			match(event, 'Milliseconds'),
			toString(formatReadableTimeDelta(value/1000)),
			if (
				match(event, 'Microseconds'),
				toString(formatReadableTimeDelta(value/1000000)),
				toString(value)
			)
		)
	) as pretty_value
from clusterAllReplicas(_CLUSTER_NAME, system.events)
order by value desc
limit 200;