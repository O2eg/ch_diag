# Active Parts By Partition

Raw part counts with an explicit advisory threshold flag.

## Collection contract

- Source: `query:troubleshooting.partition_part_counts`.
- Timing: `once`.
- Cost class: `high`.
- Privilege profile: `clickhouse_system_read`.
- Values remain raw in JSON; adaptive units are a renderer concern.

## Interpretation

Compare the result with the target topology, collection timestamp and adjacent items. An empty result is not automatically an error; inspect collection status and diagnostics.

## Limitations

The collector applies time, row, byte and artifact budgets. Version or privilege gaps are reported explicitly and an inapplicable item is omitted from the final report.
