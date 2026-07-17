SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, event = 'MarkCacheHits') AS mark_cache_hits,
    sumIf(value, event = 'MarkCacheMisses') AS mark_cache_misses,
    sumIf(value, event = 'UncompressedCacheHits') AS uncompressed_cache_hits,
    sumIf(value, event = 'UncompressedCacheMisses') AS uncompressed_cache_misses
FROM clusterAllReplicas({{cluster}}, system.events)
GROUP BY shard_num, host
ORDER BY shard_num, host
