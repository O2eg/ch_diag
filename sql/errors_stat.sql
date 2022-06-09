select
	shardNum() as shard_num,
	hostName() as host_name,
	fqdn() as fqdn,
	sum(ProfileEvent_FailedQuery) as FailedQuery,
	sum(ProfileEvent_FailedSelectQuery) as FailedSelectQuery,
	sum(ProfileEvent_FailedInsertQuery) as FailedInsertQuery,
	sum(ProfileEvent_ReplicatedPartFailedFetches) as ReplicatedPartFailedFetches,
	sum(ProfileEvent_ReplicatedPartChecksFailed) as ReplicatedPartChecksFailed,
	sum(ProfileEvent_DistributedConnectionFailTry) as DistributedConnectionFailTry,
	sum(ProfileEvent_ReplicatedDataLoss) as ReplicatedDataLoss
from clusterAllReplicas(_CLUSTER_NAME, system.metric_log)
where
	event_time > now() - interval 7 day
group by shard_num, host_name, fqdn
order by shard_num, host_name, fqdn, FailedQuery desc;
