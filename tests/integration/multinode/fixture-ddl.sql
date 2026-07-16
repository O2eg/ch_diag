DROP DATABASE IF EXISTS chdiag_fixture ON CLUSTER chdiag_cluster SYNC;
CREATE DATABASE chdiag_fixture ON CLUSTER chdiag_cluster;

CREATE TABLE chdiag_fixture.replicated_events ON CLUSTER chdiag_cluster
(
    id UInt64,
    event_time DateTime,
    category LowCardinality(String),
    payload String
)
ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{shard}/chdiag_fixture/replicated_events',
    '{replica}'
)
ORDER BY (category, event_time, id);

CREATE TABLE chdiag_fixture.distributed_events ON CLUSTER chdiag_cluster
AS chdiag_fixture.replicated_events
ENGINE = Distributed(
    chdiag_cluster,
    chdiag_fixture,
    replicated_events,
    cityHash64(id)
);

CREATE TABLE chdiag_fixture.local_events ON CLUSTER chdiag_cluster
(
    id UInt64,
    node LowCardinality(String),
    value Int64
)
ENGINE = MergeTree
ORDER BY (node, id);

CREATE TABLE chdiag_fixture.replacing_events ON CLUSTER chdiag_cluster
(
    id UInt64,
    version UInt64,
    value String
)
ENGINE = ReplacingMergeTree(version)
ORDER BY id;

CREATE TABLE chdiag_fixture.tiny_events ON CLUSTER chdiag_cluster
(
    id UInt64,
    value String
)
ENGINE = TinyLog;

CREATE TABLE chdiag_fixture.memory_events ON CLUSTER chdiag_cluster
(
    id UInt64,
    value String
)
ENGINE = Memory;
