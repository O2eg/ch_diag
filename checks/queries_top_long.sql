select
	shardNum() as shard_num,
	hostName() as host_name,
	fqdn() as fqdn,
	current_database,
	query_start_time,
	query_duration_ms,
	query,
	type,
	read_rows,
	read_bytes,
	formatReadableSize(memory_usage) as memory_usage
from clusterAllReplicas(test_cluster, system.query_log)
where
	exception_code = 0 and
	query_start_time > now() - interval 3 day and
	type = 'QueryFinish'
order by query_duration_ms desc
limit 50;
