select
	shardNum() as shard_num,
	hostName() as host_name,
	fqdn() as fqdn,
	database,
	table,
	mutation_id,
	command,
	any(create_time) as create_time,
	any(latest_fail_time) as latest_fail_time_v,
	any(latest_fail_reason) as latest_fail_reason
from clusterAllReplicas(_CLUSTER_NAME, system.mutations)
where
	is_done = 0 and
	latest_fail_time > now() - interval 7 day
group by shard_num, host_name, fqdn, database, table, mutation_id, command
order by shard_num, host_name, fqdn, latest_fail_time_v desc
limit 100;
