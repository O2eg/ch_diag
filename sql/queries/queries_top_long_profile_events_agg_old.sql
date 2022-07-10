-- queries_top_long_profile_events_agg_old - subquery to avoid "Cannot find column _shard_num in source stream" before 20.4
-- queries_top_long_profile_events_agg_20_4 - without subquery
-- queries_top_long_profile_events_agg_20_7 - added "current_database"
-- queries_top_long_profile_events_agg_21_1 - added "normalized_query_hash"
select
	_shard_num,
	host_name,
	sum(query_duration_ms) as total_duration_ms,
	any(query) as query,
	count(1) as query_times,
	arrayDistinct(groupArray(is_initial_query)) as is_initial,
	sum(read_rows) as total_read_rows,
	sum(read_bytes) as total_read_bytes,
	--formatReadableSize(sum(read_bytes)) as p_read_bytes,
	sum(result_rows) as total_result_rows,
	sum(result_bytes) as total_result_bytes,
	--formatReadableSize(sum(result_bytes)) as p_total_result_bytes,
	sum(memory_usage) as total_memory_usage,
	--formatReadableSize(sum(memory_usage)) as p_total_memory_usage,
	event_name,
	sum(pe_value) as total_pe_value,
	if(
		match(event_name, 'Bytes|Chars'),
		formatReadableSize(sum(pe_value)),
		toString(sum(pe_value))
	) as pretty_pe_value
from (
	select
		_shard_num,
		hostName() as host_name,
		cityHash64(query) as normalized_query_hash,
		substringUTF8(query, 1, 15000) as query,
		is_initial_query,
		read_rows,
		read_bytes,
		result_rows,
		result_bytes,
		memory_usage,
		query_duration_ms,
		ProfileEvents.Names as event_name,
		ProfileEvents.Values as pe_value
	from clusterAllReplicas(_CLUSTER_NAME, system.query_log)
	array join ProfileEvents
	where
		exception_code = 0 and
		query_start_time > now() - interval 3 day and
		type = 'QueryFinish'
) t
group by _shard_num, host_name, normalized_query_hash, event_name
order by total_duration_ms desc, total_pe_value desc
limit 500;