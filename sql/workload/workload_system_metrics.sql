select
	_shard_num,
	hostName() as host_name,
	metric,
	floor(avg(value), 3) as avg_value,
	floor(max(value), 3) as max_value,
	--formatReadableSize(max(value)) as total_ram
	if(
		match(metric, 'Bytes|Chars|MemoryCode|Memory|Buffers'),
		formatReadableSize(avg(value)),
		toString(floor(avg(value), 3))
	) as pretty_avg_value,
	if(
		match(metric, 'Bytes|Chars|MemoryCode|Memory|Buffers'),
		formatReadableSize(max(value)),
		toString(floor(max(value), 3))
	) as pretty_max_value
from clusterAllReplicas(_CLUSTER_NAME, system.asynchronous_metric_log)
where
	(
		metric like 'Network%' or 
		metric like '%Memory%' or
		metric like '%CPU%' or
		metric like 'Block%'
	) and event_time > now() - interval 3 day
group by _shard_num, host_name, metric
order by _shard_num, host_name, metric
