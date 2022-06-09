select
	_shard_num,
	hostName() as host_name,
	name,
	any(value) as value,
	any(changed) as changed
from clusterAllReplicas(_CLUSTER_NAME, system.merge_tree_settings)
where
	name ilike '%memo%' or
	name ilike '%sync%' or
	name ilike '%merge%' or
	name ilike '%granul%' or
	name ilike '%min%rows%' or
	name ilike '%min%part%' or
	name ilike '%max%part%'
group by _shard_num, host_name, name
order by _shard_num, host_name, name