-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	m._shard_num,
	m.host_name,
	tuple_metric.1 as metric,
	tuple_metric.2 as sum_value,
	tuple_metric.3 as avg_value,
	tuple_metric.4 as max_value
from (
	select t.*, arrayJoin(t_s.v) as tuple_metric from (
		select
			_shard_num,
			hostName() as host_name
		from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.one)
	) t
	join (
		select
			_shard_num,
			hostName() as host_name,
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
		from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.metric_log)
		where event_time > now() - interval 3 day
		group by _shard_num, host_name
	) t_s on t._shard_num = t_s._shard_num and t.host_name = t_s.host_name
) m
order by _shard_num, host_name, metric
