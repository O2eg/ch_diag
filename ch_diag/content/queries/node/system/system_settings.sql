-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	name,
	value,
	changed
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.settings)
where
	name like '%thread%' or
	name like '%pool%' or
	name like '%memo%' or
	name like '%sync%' or
	name like '%optimiz%' or
	name like '%bytes%'
order by _shard_num, host_name, name