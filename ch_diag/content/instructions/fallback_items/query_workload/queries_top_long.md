# Fallback: Top Individual Long Queries

## What this item shows
- A bounded list of individual long-running queries collected when normalized aggregation cannot complete.

## What to watch
- Large duration, read volume, memory use, or repeated expensive statements in the degraded sample.

## Common fault causes
- The primary aggregation exceeded its time or read budget while scanning a large query log.

## Automatic evaluation
- This fallback does not preserve normalized-query aggregation and must be treated as degraded evidence.

## Checklist
- Review the fallback trigger, time window, row-limit warning, and individual query examples before drawing conclusions.
