select
	_shard_num,
	hostName() as host_name,
	database,
	table,
	count(1) as count_detached_parts,
	arrayDistinct(groupArray(reason)) as reasons
from clusterAllReplicas(_CLUSTER_NAME, system.detached_parts)
group by _shard_num, host_name, database, table
order by count_detached_parts desc
limit 1000;