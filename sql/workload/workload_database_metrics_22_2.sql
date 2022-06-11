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
			hostName() as host_name,
			array(
				tuple(
					'Query',
					toUInt64(sum(ProfileEvent_Query)),
					toFloat64(avg(ProfileEvent_Query)),
					toUInt64(max(ProfileEvent_Query))
				),
				tuple(
					'SelectQuery',
					toUInt64(sum(ProfileEvent_SelectQuery)),
					toFloat64(avg(ProfileEvent_SelectQuery)),
					toUInt64(max(ProfileEvent_SelectQuery))
				),
				tuple(
					'InsertQuery',
					toUInt64(sum(ProfileEvent_InsertQuery)),
					toFloat64(avg(ProfileEvent_InsertQuery)),
					toUInt64(max(ProfileEvent_InsertQuery))
				),
				tuple(
					'AsyncInsertQuery',
					toUInt64(sum(ProfileEvent_AsyncInsertQuery)),
					toFloat64(avg(ProfileEvent_AsyncInsertQuery)),
					toUInt64(max(ProfileEvent_AsyncInsertQuery))
				),
				tuple(
					'AsyncInsertBytes',
					toUInt64(sum(ProfileEvent_AsyncInsertBytes)),
					toFloat64(avg(ProfileEvent_AsyncInsertBytes)),
					toUInt64(max(ProfileEvent_AsyncInsertBytes))
				),
				tuple(
					'InsertedRows',
					toUInt64(sum(ProfileEvent_InsertedRows)),
					toFloat64(avg(ProfileEvent_InsertedRows)),
					toUInt64(max(ProfileEvent_InsertedRows))
				),
				tuple(
					'InsertedBytes',
					toUInt64(sum(ProfileEvent_InsertedBytes)),
					toFloat64(avg(ProfileEvent_InsertedBytes)),
					toUInt64(max(ProfileEvent_InsertedBytes))
				),
				tuple(
					'DelayedInserts',
					toUInt64(sum(ProfileEvent_DelayedInserts)),
					toFloat64(avg(ProfileEvent_DelayedInserts)),
					toUInt64(max(ProfileEvent_DelayedInserts))
				),
				tuple(
					'RejectedInserts',
					toUInt64(sum(ProfileEvent_RejectedInserts)),
					toFloat64(avg(ProfileEvent_RejectedInserts)),
					toUInt64(max(ProfileEvent_RejectedInserts))
				),
				tuple(
					'Merge',
					toUInt64(sum(ProfileEvent_Merge)),
					toFloat64(avg(ProfileEvent_Merge)),
					toUInt64(max(ProfileEvent_Merge))
				),
				tuple(
					'DiskSpaceReservedForMerge',
					toUInt64(sum(CurrentMetric_DiskSpaceReservedForMerge)),
					toFloat64(avg(CurrentMetric_DiskSpaceReservedForMerge)),
					toUInt64(max(CurrentMetric_DiskSpaceReservedForMerge))
				),
				tuple(
					'MergedRows',
					toUInt64(sum(ProfileEvent_MergedRows)),
					toFloat64(avg(ProfileEvent_MergedRows)),
					toUInt64(max(ProfileEvent_MergedRows))
				),
				tuple(
					'ReplicatedPartMerges',
					toUInt64(sum(ProfileEvent_ReplicatedPartMerges)),
					toFloat64(avg(ProfileEvent_ReplicatedPartMerges)),
					toUInt64(max(ProfileEvent_ReplicatedPartMerges))
				),
				tuple(
					'ReplicatedPartFetchesOfMerged',
					toUInt64(sum(ProfileEvent_ReplicatedPartFetchesOfMerged)),
					toFloat64(avg(ProfileEvent_ReplicatedPartFetchesOfMerged)),
					toUInt64(max(ProfileEvent_ReplicatedPartFetchesOfMerged))
				),
				tuple(
					'ExternalSortMerge',
					toUInt64(sum(ProfileEvent_ExternalSortMerge)),
					toFloat64(avg(ProfileEvent_ExternalSortMerge)),
					toUInt64(max(ProfileEvent_ExternalSortMerge))
				),
				tuple(
					'ArenaAllocBytes',
					toUInt64(sum(ProfileEvent_ArenaAllocBytes)),
					toFloat64(avg(ProfileEvent_ArenaAllocBytes)),
					toUInt64(max(ProfileEvent_ArenaAllocBytes))
				),
				tuple(
					'ZooKeeperWaitMicroseconds',
					toUInt64(sum(ProfileEvent_ZooKeeperWaitMicroseconds)),
					toFloat64(avg(ProfileEvent_ZooKeeperWaitMicroseconds)),
					toUInt64(max(ProfileEvent_ZooKeeperWaitMicroseconds))
				),
				tuple(
					'ZooKeeperBytesSent',
					toUInt64(sum(ProfileEvent_ZooKeeperBytesSent)),
					toFloat64(avg(ProfileEvent_ZooKeeperBytesSent)),
					toUInt64(max(ProfileEvent_ZooKeeperBytesSent))
				),
				tuple(
					'ZooKeeperBytesReceived',
					toUInt64(sum(ProfileEvent_ZooKeeperBytesReceived)),
					toFloat64(avg(ProfileEvent_ZooKeeperBytesReceived)),
					toUInt64(max(ProfileEvent_ZooKeeperBytesReceived))
				),
				tuple(
					'ZooKeeperSession',
					toUInt64(sum(CurrentMetric_ZooKeeperSession)),
					toFloat64(avg(CurrentMetric_ZooKeeperSession)),
					toUInt64(max(CurrentMetric_ZooKeeperSession))
				)
			) as v
		from clusterAllReplicas(_CLUSTER_NAME, system.metric_log)
		where event_time > now() - interval 3 day
		group by _shard_num, host_name
	) t_s on t._shard_num = t_s._shard_num and t.host_name = t_s.host_name 
) m
order by _shard_num, host_name, metric
