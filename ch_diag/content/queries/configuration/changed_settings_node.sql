SELECT
    hostName() AS host_name,
    name,
    value,
    changed
FROM system.settings
WHERE changed
ORDER BY name
