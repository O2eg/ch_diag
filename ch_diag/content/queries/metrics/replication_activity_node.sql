SELECT
    hostName() AS host,
    sumIf(value, metric = 'ReplicatedFetch') AS replicated_fetches,
    sumIf(value, metric = 'ReplicatedSend') AS replicated_sends
FROM system.metrics
