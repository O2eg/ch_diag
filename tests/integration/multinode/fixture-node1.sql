INSERT INTO chdiag_fixture.replicated_events VALUES
    (1, '2026-01-01 00:00:01', 'direct', 'node1-a'),
    (2, '2026-01-01 00:00:02', 'direct', 'node1-b'),
    (3, '2026-01-01 00:00:03', 'direct', 'node1-c');

INSERT INTO chdiag_fixture.distributed_events VALUES
    (10, '2026-01-01 00:01:00', 'distributed', 'routed-a'),
    (11, '2026-01-01 00:01:01', 'distributed', 'routed-b'),
    (12, '2026-01-01 00:01:02', 'distributed', 'routed-c');

INSERT INTO chdiag_fixture.local_events VALUES (1, 'node1', 10), (2, 'node1', 20);
INSERT INTO chdiag_fixture.replacing_events VALUES (1, 1, 'old'), (1, 2, 'new');
INSERT INTO chdiag_fixture.tiny_events VALUES (1, 'node1');
INSERT INTO chdiag_fixture.memory_events VALUES (1, 'node1');
