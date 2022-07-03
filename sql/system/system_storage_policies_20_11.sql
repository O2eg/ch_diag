select
	_shard_num,
	hostName() as host_name,
	policy_name,
	volume_name,
	disks
	max_data_part_size,
	move_factor,
	prefer_not_to_merge
from clusterAllReplicas(_CLUSTER_NAME, system.storage_policies)
order by _shard_num, host_name, policy_name, volume_name