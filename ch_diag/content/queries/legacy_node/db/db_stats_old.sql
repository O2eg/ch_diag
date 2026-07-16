-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	database,
	count(1) as total_tables,
	length(arrayDistinct(groupArray(concat(toString(_shard_num), '_', hostName())))) as count_hosts,
	arrayStringConcat(
		arraySort(arrayDistinct(groupArray(concat(toString(_shard_num), '_', hostName())))),
		'<br>'
	) as hosts
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.tables)
where database not in ('_system', 'system', 'information_schema', 'INFORMATION_SCHEMA')
group by database
order by hosts, total_tables desc