-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	host_name,
	database,
	table,
	count(1) as count_detached_parts,
	arrayDistinct(groupArray(reason)) as reasons
from (
	select
		_shard_num,
		hostName() as host_name,
		database,
		table,
		reason
	from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.detached_parts)
) t
group by _shard_num, host_name, database, table
order by count_detached_parts desc
limit 1000;