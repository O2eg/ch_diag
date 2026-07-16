-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	database,
	name,
	any(engine) as engine,
	any(replaceRegexpAll(create_table_query, 'PASSWORD\s\'.*?\'', '...')) as create_table_query,
	sum(toInt64(total_rows)) as total_rows,
	sum(toInt64(total_bytes)) as _total_bytes
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.tables)
where database not in ('_system', 'system', 'information_schema', 'INFORMATION_SCHEMA')
group by _shard_num, host_name, database, name
order by _total_bytes desc nulls last
limit 100;