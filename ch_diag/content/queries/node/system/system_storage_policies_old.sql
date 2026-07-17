-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	policy_name,
	volume_name,
	disks
	max_data_part_size,
	move_factor
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.storage_policies)
order by _shard_num, host_name, policy_name, volume_name