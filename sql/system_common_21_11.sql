select
	_shard_num,
	hostName() as host_name,
	formatReadableSize(filesystemAvailable()) as fs_available,
	formatReadableSize(filesystemCapacity()) as fs_capacity,
	getOSKernelVersion() as os_version,
	version() as ch_version,
	getServerPort('tcp_port') as tcp_port,
	getServerPort('http_port') as http_port
from clusterAllReplicas(_CLUSTER_NAME, system.one)
order by _shard_num, host_name;