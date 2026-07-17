-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	database,
	sum(total_rows) as total_rows,
	sum(total_bytes) as total_bytes
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.tables)
where database not in ('INFORMATION_SCHEMA', 'information_schema')
group by _shard_num, host_name, database
order by _shard_num, total_bytes desc nulls last;