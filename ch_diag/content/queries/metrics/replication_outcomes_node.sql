SELECT
    hostName() AS host,
    sumIf(value, event = 'ReplicatedPartFetches') AS replicated_part_fetches,
    sumIf(value, event = 'ReplicatedPartFailedFetches') AS replicated_part_failed_fetches,
    sumIf(value, event = 'ReplicatedPartMerges') AS replicated_part_merges,
    sumIf(value, event = 'ReplicatedDataLoss') AS replicated_data_loss
FROM system.events
