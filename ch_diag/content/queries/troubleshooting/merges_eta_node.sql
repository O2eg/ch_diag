SELECT
    database,
    table,
    partition_id,
    is_mutation,
    elapsed AS elapsed_seconds,
    progress,
    if(progress > 0, elapsed * (1 - progress) / progress, NULL) AS estimated_remaining_seconds,
    num_parts,
    total_size_bytes_compressed,
    bytes_read_uncompressed,
    bytes_written_uncompressed,
    memory_usage AS memory_bytes,
    result_part_name
FROM system.merges
ORDER BY estimated_remaining_seconds DESC NULLS LAST, database, table
LIMIT 200
