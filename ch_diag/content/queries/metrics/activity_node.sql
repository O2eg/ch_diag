SELECT
    hostName() AS host,
    sumIf(value, metric = 'Query') AS current_queries,
    sumIf(value, metric = 'Merge') AS current_merges,
    sumIf(value, metric = 'PartMutation') AS current_mutations,
    sumIf(value, metric = 'DistributedSend') AS distributed_sends
FROM system.metrics
