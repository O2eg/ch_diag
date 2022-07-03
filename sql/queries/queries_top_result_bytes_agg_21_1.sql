-- queries_top_result_bytes_agg_old - subquery to avoid "Cannot find column _shard_num in source stream" before 20.4
-- queries_top_result_bytes_agg_20_4 - without subquery
-- queries_top_result_bytes_agg_20_7 - added "current_database"
-- queries_top_result_bytes_agg_21_1 - added "normalized_query_hash"
select
	_shard_num,
	hostName() as host_name,
	sum(query_duration_ms) as total_duration_ms,
	any(substringUTF8(query, 1, 15000)) as query,
	count(1) as query_times,
	arrayDistinct(groupArray(is_initial_query)) as is_initial,
	sum(read_rows) as total_read_rows,
	sum(read_bytes) as total_read_bytes,
	formatReadableSize(sum(read_bytes)) as p_read_bytes,
	sum(result_rows) as total_result_rows,
	sum(result_bytes) as total_result_bytes,
	formatReadableSize(sum(result_bytes)) as p_total_result_bytes,
	sum(memory_usage) as total_memory_usage,
	formatReadableSize(sum(memory_usage)) as p_total_memory_usage
from clusterAllReplicas(_CLUSTER_NAME, system.query_log)
where
	exception_code = 0 and
	query_start_time > now() - interval 3 day and
	type = 'QueryFinish'
group by _shard_num, host_name, current_database, normalized_query_hash
order by total_result_bytes desc
limit 30;