select
	T1._shard_num as _shard_num,
	T1.host_name as host_name,
	T1.fs_available as fs_available,
	T1.fs_capacity as fs_capacity,
	T1.os_version as os_version,
	T1.ch_version as ch_version,
	T1.uptime as uptime,
	T1.tcp_port as tcp_port,
	T1.http_port as http_port,
	T2.total_ram as total_ram,
	T3.available_ram_avg as available_ram_avg
from (
	select
		_shard_num,
		hostName() as host_name,
		formatReadableSize(filesystemAvailable()) as fs_available,
		formatReadableSize(filesystemCapacity()) as fs_capacity,
		getOSKernelVersion() as os_version,
		version() as ch_version,
		formatReadableTimeDelta(uptime()) as uptime,
		getServerPort('tcp_port') as tcp_port,
		getServerPort('http_port') as http_port
	from clusterAllReplicas(_CLUSTER_NAME, system.one)
) T1
join (
	select
		_shard_num,
		hostName() as host_name,
		formatReadableSize(max(value)) as total_ram
	from clusterAllReplicas(_CLUSTER_NAME, system.asynchronous_metric_log)
	where metric = 'OSMemoryTotal' and event_time > now() - interval 1 day
	group by _shard_num, host_name
) T2 on T1._shard_num = T2._shard_num and T1.host_name = T2.host_name
join (
	select
		_shard_num,
		hostName() as host_name,
		formatReadableSize(avg(value)) as available_ram_avg
	from clusterAllReplicas(_CLUSTER_NAME, system.asynchronous_metric_log)
	where metric = 'OSMemoryAvailable' and event_time > now() - interval 1 day
	group by _shard_num, host_name
) T3 on T1._shard_num = T3._shard_num and T1.host_name = T3.host_name
order by T1._shard_num, T1.host_name;