select
	_shard_num,
	hostName() as host_name,
	formatReadableSize(filesystemAvailable()) as fs_available,
	formatReadableSize(filesystemCapacity()) as fs_capacity,
	version() as ch_version,
	uptime() as uptime
from clusterAllReplicas(_CLUSTER_NAME, system.one)
order by _shard_num, host_name;