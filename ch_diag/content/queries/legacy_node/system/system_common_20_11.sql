-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	filesystemAvailable() as fs_available,
	filesystemCapacity() as fs_capacity,
	version() as ch_version,
	formatReadableTimeDelta(uptime()) as uptime
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.one)
order by _shard_num, host_name;