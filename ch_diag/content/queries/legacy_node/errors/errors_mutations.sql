-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
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
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.mutations)
where
	is_done = 0 and
	latest_fail_time > now() - interval 7 day
order by latest_fail_time desc
limit 100