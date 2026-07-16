select
	database,
	name,
	engine,
	count(1) as count_tables,
	arrayStringConcat(
		arraySort(arrayDistinct(groupArray(concat(toString(_shard_num), '_', hostName())))),
		'<br>'
	) as hosts
from clusterAllReplicas({{cluster}}, system.tables)
where database not in ('_system', 'system', 'information_schema', 'INFORMATION_SCHEMA')
group by database, name, engine
having count_tables < (select count(1) from system.clusters where cluster = {{cluster}})
order by count_tables desc nulls last