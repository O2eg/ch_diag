-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
SELECT
	_shard_num,
	hostName() as host_name,
	database,
	table,
	mutation_id,
	command,
	create_time,
	parts_to_do_names,
	parts_to_do,
	is_done,
	latest_failed_part,
	latest_fail_time,
	latest_fail_reason
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.mutations)
WHERE is_done = 0
ORDER BY create_time DESC
limit 1000