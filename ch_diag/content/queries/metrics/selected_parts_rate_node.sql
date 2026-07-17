SELECT
    hostName() AS host,
    sumIf(value, event = 'SelectedParts') AS selected_parts,
    sumIf(value, event = 'SelectedMarks') AS selected_marks,
    sumIf(value, event = 'SelectedRanges') AS selected_ranges
FROM system.events
