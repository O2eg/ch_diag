select
	_shard_num,
	hostName() as host_name,
	filesystemAvailable() as fs_available,
	filesystemCapacity() as fs_capacity,
	version() as ch_version,
	uptime() as uptime
from clusterAllReplicas({{cluster}}, system.one)
order by _shard_num, host_name;