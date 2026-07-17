-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	name,
	free_space as free_space,
	total_space as total_space,
	keep_free_space
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.disks)
order by _shard_num, host_name, name