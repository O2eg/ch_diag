select
	database,
	name,
	engine,
	count(1) as count_tables,
	any(replaceRegexpAll(create_table_query, 'PASSWORD\s\'.*?\'', '...')) as create_table_query,
	sum(toInt64(total_rows)) as total_rows,
	sum(toInt64(total_bytes)) as _total_bytes,
	formatReadableSize(sum(toInt64(total_bytes))) as pretty_total_bytes,
	arrayStringConcat(
		arraySort(arrayDistinct(groupArray(concat(toString(_shard_num), '_', hostName())))),
		'<br>'
	) as hosts
from clusterAllReplicas(_CLUSTER_NAME, system.tables)
where database not in ('_system', 'system', 'information_schema', 'INFORMATION_SCHEMA')
group by database, name, engine
having count_tables = (select count(1) from system.clusters where cluster = '_CLUSTER_NAME')
order by _total_bytes desc nulls last