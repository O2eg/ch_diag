select
	shardNum() as shard_num,
	hostName() as host_name,
	fqdn() as fqdn,
	policy_name,
	volume_name,
	any(disks) as disks,
	any(max_data_part_size) as max_data_part_size,
	any(move_factor) as move_factor,
	any(prefer_not_to_merge) as prefer_not_to_merge
from clusterAllReplicas(_CLUSTER_NAME, system.storage_policies)
group by shard_num, host_name, fqdn, policy_name, volume_name
order by shard_num, host_name, fqdn, policy_name, volume_name