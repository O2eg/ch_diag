select
	_shard_num,
	hostName() as host_name,
	sum(ProfileEvent_FailedQuery) as FailedQuery,
	sum(ProfileEvent_FailedSelectQuery) as FailedSelectQuery,
	sum(ProfileEvent_FailedInsertQuery) as FailedInsertQuery,
	sum(ProfileEvent_ReplicatedPartFailedFetches) as ReplicatedPartFailedFetches,
	sum(ProfileEvent_ReplicatedPartChecksFailed) as ReplicatedPartChecksFailed,
	sum(ProfileEvent_DistributedConnectionFailTry) as DistributedConnectionFailTry,
	sum(ProfileEvent_ReplicatedDataLoss) as ReplicatedDataLoss,
	sum(CurrentMetric_BrokenDistributedFilesToInsert) as BrokenDistributedFilesToInsert
from clusterAllReplicas(_CLUSTER_NAME, system.metric_log)
where
	event_time > now() - interval 7 day
group by _shard_num, host_name
order by _shard_num, host_name, FailedQuery desc;
