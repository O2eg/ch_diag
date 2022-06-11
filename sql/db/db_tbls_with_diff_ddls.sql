select
	database,
	name,
	engine,
	count(distinct(cityHash64(create_table_query))) as count_diff,
	arrayStringConcat(
		arrayDistinct(groupArray(create_table_query)),
		'<br>'
	) as ddls,
	length(arrayDistinct(groupArray(concat(toString(_shard_num), '_', hostName())))) as count_hosts,
	arrayStringConcat(
		arraySort(arrayDistinct(groupArray(concat(toString(_shard_num), '_', hostName())))),
		'<br>'
	) as hosts
from clusterAllReplicas(_CLUSTER_NAME, system.tables)
where database not in ('_system', 'system', 'information_schema', 'INFORMATION_SCHEMA')
group by database, name, engine
having count_diff > 1