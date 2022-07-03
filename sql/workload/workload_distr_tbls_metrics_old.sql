-- subquery to avoid "Cannot find column _shard_num in source stream"
select
	m._shard_num, 
	m.host_name,
	tuple_metric.1 as metric,
	tuple_metric.2 as sum_value,
	round(tuple_metric.3, 2) as avg_value,
	tuple_metric.4 as max_value
from (
	select t.*, arrayJoin(t_s.v) as tuple_metric from (
		select
			_shard_num,
			hostName() as host_name
		from clusterAllReplicas(_CLUSTER_NAME, system.one) 
	) t
	join (
		select
			_shard_num,
			host_name,
			array(
				tuple(
					'DistributedConnectionFailTry',
					toUInt64(sum(ProfileEvent_DistributedConnectionFailTry)),
					toFloat64(avg(ProfileEvent_DistributedConnectionFailTry)),
					toUInt64(max(ProfileEvent_DistributedConnectionFailTry))
				),
				tuple(
					'DistributedConnectionMissingTable',
					toUInt64(sum(ProfileEvent_DistributedConnectionMissingTable)),
					toFloat64(avg(ProfileEvent_DistributedConnectionMissingTable)),
					toUInt64(max(ProfileEvent_DistributedConnectionMissingTable))
				),
				tuple(
					'DistributedConnectionStaleReplica',
					toUInt64(sum(ProfileEvent_DistributedConnectionStaleReplica)),
					toFloat64(avg(ProfileEvent_DistributedConnectionStaleReplica)),
					toUInt64(max(ProfileEvent_DistributedConnectionStaleReplica))
				),
				tuple(
					'DistributedConnectionFailAtAll',
					toUInt64(sum(ProfileEvent_DistributedConnectionFailAtAll)),
					toFloat64(avg(ProfileEvent_DistributedConnectionFailAtAll)),
					toUInt64(max(ProfileEvent_DistributedConnectionFailAtAll))
				),
				tuple(
					'DistributedSyncInsertionTimeoutExceeded',
					toUInt64(sum(ProfileEvent_DistributedSyncInsertionTimeoutExceeded)),
					toFloat64(avg(ProfileEvent_DistributedSyncInsertionTimeoutExceeded)),
					toUInt64(max(ProfileEvent_DistributedSyncInsertionTimeoutExceeded))
				),
				tuple(
					'DistributedSend',
					toUInt64(sum(CurrentMetric_DistributedSend)),
					toFloat64(avg(CurrentMetric_DistributedSend)),
					toUInt64(max(CurrentMetric_DistributedSend))
				),
				tuple(
					'DistributedFilesToInsert',
					toUInt64(sum(CurrentMetric_DistributedFilesToInsert)),
					toFloat64(avg(CurrentMetric_DistributedFilesToInsert)),
					toUInt64(max(CurrentMetric_DistributedFilesToInsert))
				)
			) as v
		from (
			select
				_shard_num,
				hostName() as host_name,
				ProfileEvent_DistributedConnectionFailTry,
				ProfileEvent_DistributedConnectionMissingTable,
				ProfileEvent_DistributedConnectionStaleReplica,
				ProfileEvent_DistributedConnectionFailAtAll,
				ProfileEvent_DistributedSyncInsertionTimeoutExceeded,
				CurrentMetric_DistributedSend,
				CurrentMetric_DistributedFilesToInsert
			from clusterAllReplicas(_CLUSTER_NAME, system.metric_log)
			where event_time > now() - interval 3 day
		)
		group by _shard_num, host_name
	) t_s on t._shard_num = t_s._shard_num and t.host_name = t_s.host_name 
) m
order by _shard_num, host_name, metric