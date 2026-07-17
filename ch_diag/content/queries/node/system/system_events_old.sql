-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	event,
	value
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.events)
order by value desc
limit 200;