# Fallback: Top Individual Queries By Result Bytes

## What this item shows
- A bounded list of individual high-result-volume queries used when normalized aggregation cannot complete.

## What to watch
- Queries returning unusually large row or byte counts and repeated client-side over-fetching patterns.

## Common fault causes
- The aggregate source exceeded its timeout or read budget over a large query-log window.

## Automatic evaluation
- Individual executions replace normalized aggregates, so totals across repeated statements are incomplete.

## Checklist
- Check the primary failure, result row limit, time range, and whether several rows share the same query pattern.
