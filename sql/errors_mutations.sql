select
	_shard_num,
	hostName() as host_name,
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
group by _shard_num, host_name, database, table, mutation_id, command
order by _shard_num, host_name, latest_fail_time_v desc
limit 100;
