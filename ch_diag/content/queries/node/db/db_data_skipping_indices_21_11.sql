-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	_shard_num,
	hostName() as host_name,
	database,
	table,
	name,
	type,
	expr,
	granularity,
	data_compressed_bytes,
	data_uncompressed_bytes,
	marks
from (SELECT 1 AS _shard_num, 1 AS _replica_num, * FROM system.data_skipping_indices)
order by name;