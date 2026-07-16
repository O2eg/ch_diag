# ClickHouse Server Process Tree

Main ClickHouse server selected by the connected native port and its child processes.

## Collection contract

- Source: `script:clickhouse.process_tree`.
- Timing: `once`.
- Cost class: `low`.
- Privilege profile: `host_read`.
- Values remain raw in JSON; adaptive units are a renderer concern.

## Interpretation

Compare the result with the target topology, collection timestamp and adjacent items. An empty result is not automatically an error; inspect collection status and diagnostics.

## Limitations

The collector applies time, row, byte and artifact budgets. Version or privilege gaps are reported explicitly and an inapplicable item is omitted from the final report.
