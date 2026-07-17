SELECT
    _shard_num AS shard_num,
    hostName() AS host,
    sumIf(value, event = 'SelectedParts') AS selected_parts,
    sumIf(value, event = 'SelectedMarks') AS selected_marks,
    sumIf(value, event = 'SelectedRanges') AS selected_ranges
FROM clusterAllReplicas({{cluster}}, system.events)
GROUP BY shard_num, host
ORDER BY shard_num, host
