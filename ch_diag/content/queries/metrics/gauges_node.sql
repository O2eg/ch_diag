SELECT
    hostName() AS host,
    sumIf(value, metric = 'Query') AS current_queries,
    sumIf(value, metric = 'Merge') AS current_merges,
    sumIf(value, metric = 'PartMutation') AS current_mutations,
    sumIf(value, metric = 'DistributedSend') AS distributed_sends,
    sumIf(value, metric = 'MemoryTracking') AS memory_bytes,
    sumIf(value, metric = 'ReplicatedFetch') AS replicated_fetches,
    sumIf(value, metric = 'ReplicatedSend') AS replicated_sends,
    sumIf(value, metric = 'ReadonlyReplica') AS readonly_replicas
FROM system.metrics
