select
	_shard_num,
	hostName() as host_name,
	name,
	value,
	changed
from clusterAllReplicas({{cluster}}, system.settings)
where
	name like '%thread%' or
	name like '%pool%' or
	name like '%memo%' or
	name like '%sync%' or
	name like '%optimiz%' or
	name like '%bytes%'
order by _shard_num, host_name, name