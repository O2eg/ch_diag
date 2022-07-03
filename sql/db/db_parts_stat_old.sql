SELECT
	_shard_num,
	host_name,
	database,
	table,
	count(partition) as partitions,
	sum(parts_count) parts,
	max(parts_count) max_parts_per_partition
FROM
(
	SELECT
		_shard_num,
		host_name,
		database,
		table,
		partition,
		count(1) as parts_count
	from (
		SELECT
			_shard_num,
			hostName() as host_name,
			database,
			table,
			partition
		from clusterAllReplicas(_CLUSTER_NAME, system.parts)
		WHERE active
	) t
	GROUP BY _shard_num, host_name, database, table, partition
) partitions
GROUP BY _shard_num, host_name, database, table
ORDER BY max_parts_per_partition DESC
LIMIT 300