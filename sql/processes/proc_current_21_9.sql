SELECT
	_shard_num,
	hostName() as host_name,
	query,
	query_id,
	is_initial_query,
	initial_query_id,
	round(elapsed, 1) as _elapsed,
	read_rows,
	read_bytes,
	written_rows,
	written_bytes,
	memory_usage,
	peak_memory_usage,
	formatReadableSize(memory_usage) as pretty_memory_usage,
	formatReadableSize(peak_memory_usage) as pretty_peak_memory_usage
from clusterAllReplicas(_CLUSTER_NAME, system.processes)
order by _elapsed desc
limit 1000