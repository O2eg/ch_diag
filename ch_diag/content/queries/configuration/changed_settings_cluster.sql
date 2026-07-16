SELECT
    hostName() AS host_name,
    name,
    value,
    changed
FROM clusterAllReplicas({{cluster}}, system.settings)
WHERE changed
ORDER BY host_name, name
