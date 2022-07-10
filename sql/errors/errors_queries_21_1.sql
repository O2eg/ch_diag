select
	_shard_num,
	hostName() as host_name,
	any(type) as type,
	exception_code,
	any(exception) as exception,
	any(is_initial_query) as is_initial_query,
	any(client_name) as client_name,
	count(1) as fail_times,
	any(query) as query
from clusterAllReplicas(_CLUSTER_NAME, system.query_log)
where
	exception_code <> 0 and
	event_time > now() - interval 7 day
group by _shard_num, host_name, exception_code, normalized_query_hash
order by _shard_num, host_name, fail_times desc
limit 100;