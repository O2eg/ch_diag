-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	floor(avg(CurrentMetric_BackgroundMergesAndMutationsPoolTask), 2) as MergesAndMutationsPoolTask,
	floor(avg(CurrentMetric_BackgroundFetchesPoolTask), 2) as FetchesPoolTask,
	floor(avg(CurrentMetric_BackgroundCommonPoolTask), 2) as CommonPoolTask,
	floor(avg(CurrentMetric_BackgroundMovePoolTask), 2) as MovePoolTask,
	floor(avg(CurrentMetric_BackgroundSchedulePoolTask), 2) as SchedulePoolTask,
	floor(avg(CurrentMetric_BackgroundBufferFlushSchedulePoolTask), 2) as BufferFlushSchedulePoolTask,
	floor(avg(CurrentMetric_BackgroundDistributedSchedulePoolTask), 2) as DistributedSchedulePoolTask,
	floor(avg(CurrentMetric_BackgroundMessageBrokerSchedulePoolTask), 2) as MessageBrokerSchedulePoolTask
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.metric_log)
where
	event_time > now() - interval 7 day
group by _shard_num, host_name
order by _shard_num, host_name;