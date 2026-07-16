-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	host_name,
	sum(ProfileEvent_ReplicatedPartFailedFetches) as ReplicatedPartFailedFetches,
	sum(ProfileEvent_ReplicatedPartChecksFailed) as ReplicatedPartChecksFailed,
	sum(ProfileEvent_DistributedConnectionFailTry) as DistributedConnectionFailTry
from (
	select
		_shard_num,
		hostName() as host_name,
		ProfileEvent_ReplicatedPartFailedFetches,
		ProfileEvent_ReplicatedPartChecksFailed,
		ProfileEvent_DistributedConnectionFailTry
	from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.metric_log)
	where
		event_time > now() - interval 7 day
) t
group by _shard_num, host_name
order by _shard_num, host_name, DistributedConnectionFailTry desc;
