SELECT
    hostName() AS host,
    sumIf(value, event = 'MarkCacheHits') AS mark_cache_hits,
    sumIf(value, event = 'MarkCacheMisses') AS mark_cache_misses,
    sumIf(value, event = 'UncompressedCacheHits') AS uncompressed_cache_hits,
    sumIf(value, event = 'UncompressedCacheMisses') AS uncompressed_cache_misses
FROM system.events
