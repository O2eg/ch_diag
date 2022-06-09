select
	shardNum() as shard_num,
	hostName() as host_name,
	fqdn() as fqdn,
	name,
	any(code) as code,
	any(value) as value,
	any(remote) as remote,
	any(last_error_message) as last_error_message
from clusterAllReplicas(_CLUSTER_NAME, system.errors)
group by shard_num, host_name, fqdn, name
order by shard_num, host_name, fqdn, value desc
limit 100;