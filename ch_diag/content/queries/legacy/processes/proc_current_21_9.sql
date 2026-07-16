SELECT
	_shard_num,
	hostName() as host_name,
	query,
	query_id,
	is_initial_query,
	initial_query_id,
	elapsed as _elapsed,
	read_rows,
	read_bytes,
	written_rows,
	written_bytes,
	memory_usage,
	peak_memory_usage
from clusterAllReplicas({{cluster}}, system.processes)
order by _elapsed desc
limit 1000