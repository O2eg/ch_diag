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
					'ZooKeeperUserExceptions',
					toUInt64(sum(ProfileEvent_ZooKeeperUserExceptions)),
					toFloat64(avg(ProfileEvent_ZooKeeperUserExceptions)),
					toUInt64(max(ProfileEvent_ZooKeeperUserExceptions))
				),
				tuple(
					'ZooKeeperHardwareExceptions',
					toUInt64(sum(ProfileEvent_ZooKeeperHardwareExceptions)),
					toFloat64(avg(ProfileEvent_ZooKeeperHardwareExceptions)),
					toUInt64(max(ProfileEvent_ZooKeeperHardwareExceptions))
				),
				tuple(
					'ZooKeeperOtherExceptions',
					toUInt64(sum(ProfileEvent_ZooKeeperOtherExceptions)),
					toFloat64(avg(ProfileEvent_ZooKeeperOtherExceptions)),
					toUInt64(max(ProfileEvent_ZooKeeperOtherExceptions))
				)
			) as v
		from (
			select
				_shard_num,
				hostName() as host_name,
				ProfileEvent_ZooKeeperUserExceptions,
				ProfileEvent_ZooKeeperHardwareExceptions,
				ProfileEvent_ZooKeeperOtherExceptions
			from clusterAllReplicas(_CLUSTER_NAME, system.metric_log)
			where event_time > now() - interval 3 day
		) t
		group by _shard_num, host_name
	) t_s on t._shard_num = t_s._shard_num and t.host_name = t_s.host_name 
) m
order by _shard_num, host_name, metric;