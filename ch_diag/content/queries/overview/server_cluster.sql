SELECT
    hostName() AS host_name,
    version() AS server_version,
    currentDatabase() AS current_database,
    currentUser() AS current_user
FROM clusterAllReplicas({{cluster}}, system.one)
ORDER BY host_name
