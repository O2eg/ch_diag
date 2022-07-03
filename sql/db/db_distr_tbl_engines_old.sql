select
	database,
	engine,
	count(1) as total_tables,
	length(arrayDistinct(groupArray(concat(toString(_shard_num), '_', hostName())))) as count_hosts,
	arrayStringConcat(
		arraySort(arrayDistinct(groupArray(concat(toString(_shard_num), '_', hostName())))),
		'<br>'
	) as hosts
from clusterAllReplicas(_CLUSTER_NAME, system.tables)
where database not in ('_system', 'system', 'information_schema', 'INFORMATION_SCHEMA')
group by database, engine
order by count_hosts, total_tables desc