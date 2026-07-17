select
	_shard_num,
	hostName() as host_name,
	metric,
	floor(avg(value), 3) as avg_value,
	floor(max(value), 3) as max_value
from clusterAllReplicas({{cluster}}, system.asynchronous_metric_log)
where
	(
		metric like 'Network%' or
		metric like '%Memory%' or
		metric like '%CPU%' or
		metric like 'Block%'
	) and event_time > now() - interval 3 day
group by _shard_num, host_name, metric
order by _shard_num, host_name, metric
