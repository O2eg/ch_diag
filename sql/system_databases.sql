select
	shardNum() as shard_num,
	hostName() as host_name,
	fqdn() as fqdn,
	groupArray(database) as databases
from clusterAllReplicas(_CLUSTER_NAME, system.databases)
where database not in ('INFORMATION_SCHEMA', 'information_schema')
group by shard_num, host_name, fqdn
order by shard_num, host_name, fqdn;