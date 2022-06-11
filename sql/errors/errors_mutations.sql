select
	_shard_num,
	hostName() as host_name,
	database,
	table,
	mutation_id,
	command,
	create_time,
	latest_fail_time,
	latest_fail_reason
from clusterAllReplicas(_CLUSTER_NAME, system.mutations)
where
	is_done = 0 and
	latest_fail_time > now() - interval 7 day
order by latest_fail_time desc
limit 100