# Local files that are in the queue to be sent to the shards (based on system.distribution_queue)

These local files contain new parts that are created by inserting new data into the Distributed table in asynchronous mode

## Collection contract

- Source: `query:legacy.processes.proc_distribution_queue`.
- Timing: `once`.
- Cost class: `medium`.
- Privilege profile: `clickhouse_system_read`.
- Values remain raw in JSON; adaptive units are a renderer concern.

## Interpretation

Compare the result with the target topology, collection timestamp and adjacent items. An empty result is not automatically an error; inspect collection status and diagnostics.

## Limitations

The collector applies time, row, byte and artifact budgets. Version or privilege gaps are reported explicitly and an inapplicable item is omitted from the final report.
