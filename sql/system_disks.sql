select
	shardNum() as shard_num,
	hostName() as host_name,
	fqdn() as fqdn,
	name,
	any(formatReadableSize(free_space)) as free_space,
	any(formatReadableSize(total_space)) as total_space,
	any(keep_free_space) as keep_free_space,
	any(type) as type
from clusterAllReplicas(_CLUSTER_NAME, system.disks)
group by shard_num, host_name, fqdn, name
order by shard_num, host_name, fqdn, name