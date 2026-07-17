-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	current_database as current_db,
	query_start_time,
	query_duration_ms as duration_ms,
	substringUTF8(query, 1, 15000) as query,
	is_initial_query as is_initial,
	type,
	read_rows,
	read_bytes,
	result_rows,
	result_bytes,
	memory_usage
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.query_log)
where
	exception_code = 0 and
	query_start_time > now() - interval 3 day and
	type = 'QueryFinish'
order by memory_usage desc
limit 30;