-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	name,
	engine
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.databases)
where name not in ('INFORMATION_SCHEMA', 'information_schema')
order by _shard_num, host_name, name