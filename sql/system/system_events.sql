select
	_shard_num,
	hostName() as host_name,
	event,
	any(value) as _value,
	if(
		match(event, 'Bytes|Chars|MemoryCode|Memory|Buffers'),
		formatReadableSize(any(value)),
		if (
			match(event, 'Milliseconds'),
			toString(formatReadableTimeDelta(any(value)/1000)),
			if (
				match(event, 'Microseconds'),
				toString(formatReadableTimeDelta(any(value)/1000000)),
				toString(any(value))
			)
		)
	) as pretty_value
from clusterAllReplicas(_CLUSTER_NAME, system.events)
group by _shard_num, host_name, event
order by _value desc
limit 200;
