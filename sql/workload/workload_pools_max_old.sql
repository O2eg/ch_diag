select
	_shard_num,
	hostName() as host_name,
	floor(max(CurrentMetric_BackgroundPoolTask), 2) as BackgroundPoolTask,
	floor(max(CurrentMetric_BackgroundMovePoolTask), 2) as MovePoolTask,
	floor(max(CurrentMetric_BackgroundSchedulePoolTask), 2) as SchedulePoolTask
from (
	select
		_shard_num,
		hostName() as host_name,
		CurrentMetric_BackgroundPoolTask,
		CurrentMetric_BackgroundMovePoolTask,
		CurrentMetric_BackgroundSchedulePoolTask
	from clusterAllReplicas(_CLUSTER_NAME, system.metric_log)
	where event_time > now() - interval 7 day
) t
group by _shard_num, host_name
order by _shard_num, host_name;