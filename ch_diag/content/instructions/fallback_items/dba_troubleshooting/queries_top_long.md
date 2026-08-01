# Fallback: Bounded Individual Long Queries

## What this item shows
- A bounded list of long individual executions when normalized frequency aggregation cannot complete.

## What to watch
- Repeated long statements, high read or result volume, and memory-heavy executions in the degraded sample.

## Common fault causes
- Normalization support was unavailable or frequency grouping exceeded its query-log collection budget.

## Automatic evaluation
- Individual long executions replace the normalized frequency ranking and do not preserve execution counts by query family.

## Checklist
- Review the fallback trigger, row-limit warning, query-log window, and repeated query shapes before comparison.
