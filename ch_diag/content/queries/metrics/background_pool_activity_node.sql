SELECT
    hostName() AS host,
    sumIf(value, metric = 'BackgroundMergesAndMutationsPoolTask') AS background_merge_tasks,
    sumIf(value, metric = 'BackgroundFetchesPoolTask') AS background_fetch_tasks,
    sumIf(value, metric = 'BackgroundMovePoolTask') AS background_move_tasks,
    sumIf(value, metric = 'BackgroundSchedulePoolTask') AS background_schedule_tasks,
    sumIf(value, metric = 'BackgroundCommonPoolTask') AS background_common_tasks
FROM system.metrics
