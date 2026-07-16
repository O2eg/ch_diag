SELECT
	database,
	table,
	name AS column,
	type,
	compression_codec,
	data_compressed_bytes,
	data_uncompressed_bytes,
	marks_bytes,
	if(data_compressed_bytes = 0, NULL,
       data_uncompressed_bytes / data_compressed_bytes) AS compression_ratio,
	is_in_primary_key,
	is_in_sorting_key
FROM system.columns
WHERE database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema')
ORDER BY data_uncompressed_bytes DESC, database, table, column
LIMIT 1000
