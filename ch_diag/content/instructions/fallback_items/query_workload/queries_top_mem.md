# Fallback: Top Individual Queries By Memory

## What this item shows
- A bounded list of individual memory-heavy queries collected when normalized aggregation cannot complete.

## What to watch
- Peak memory outliers, large reads, and repeated statements that individually approach memory limits.

## Common fault causes
- Query-log volume or grouping work caused the primary aggregate query to exceed its collection budget.

## Automatic evaluation
- The fallback ranks individual executions and cannot represent cumulative memory across a normalized query family.

## Checklist
- Review the fallback trigger, configured memory limits, query window, and any row-limit coverage warning.
