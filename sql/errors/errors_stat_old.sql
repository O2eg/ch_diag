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
	from clusterAllReplicas(_CLUSTER_NAME, system.metric_log)
	where
		event_time > now() - interval 7 day
) t
group by _shard_num, host_name
order by _shard_num, host_name, DistributedConnectionFailTry desc;
