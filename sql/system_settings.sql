select
	_shard_num,
	hostName() as host_name,
	name,
	any(value) as value,
	any(changed) as changed
from clusterAllReplicas(_CLUSTER_NAME, system.settings)
where
	name ilike '%thread%' or
	name ilike '%pool%' or
	name ilike '%memo%' or
	name ilike '%sync%' or
	name ilike '%optimiz%'
group by _shard_num, host_name, name
order by _shard_num, host_name, name