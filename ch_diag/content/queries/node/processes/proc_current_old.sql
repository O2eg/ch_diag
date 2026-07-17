-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
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
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.processes)
order by _elapsed desc
limit 1000