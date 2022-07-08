select
	_shard_num,
	hostName() as host_name,
	name,
	value,
	if(
		match(name, 'memory|bytes') and toInt64OrZero(value) > 10,
		formatReadableSize(toInt64OrZero(value)),
		toString(value)
	) as pretty_value,
	changed
from clusterAllReplicas(_CLUSTER_NAME, system.settings)
where
	name like '%thread%' or
	name like '%pool%' or
	name like '%memo%' or
	name like '%sync%' or
	name like '%optimiz%' or
	name like '%bytes%'
order by _shard_num, host_name, name