SELECT
    hostName() AS host,
    sumIf(value, match(event, 'ZooKeeper|Keeper')) AS keeper_events
FROM system.events
