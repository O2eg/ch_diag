select
	_shard_num,
	hostName() as host_name,
	floor(max(CurrentMetric_BackgroundPoolTask), 2) as BackgroundPoolTask,
	floor(max(CurrentMetric_BackgroundFetchesPoolTask), 2) as FetchesPoolTask,
	floor(max(CurrentMetric_BackgroundMovePoolTask), 2) as MovePoolTask,
	floor(max(CurrentMetric_BackgroundSchedulePoolTask), 2) as SchedulePoolTask,
	floor(max(CurrentMetric_BackgroundBufferFlushSchedulePoolTask), 2) as BufferFlushSchedulePoolTask,
	floor(max(CurrentMetric_BackgroundDistributedSchedulePoolTask), 2) as DistributedSchedulePoolTask,
	floor(max(CurrentMetric_BackgroundMessageBrokerSchedulePoolTask), 2) as MessageBrokerSchedulePoolTask
from clusterAllReplicas(_CLUSTER_NAME, system.metric_log)
where
	event_time > now() - interval 7 day
group by _shard_num, host_name
order by _shard_num, host_name;