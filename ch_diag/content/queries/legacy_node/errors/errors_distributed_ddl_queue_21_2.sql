-- Generated standalone-node variant. Do not edit directly; see tools/generate_node_variants.py.
select
	entry,
	port,
	cluster,
	status,
	query,
	exception_code
from system.distributed_ddl_queue
WHERE status != 'Finished' or exception_code != 0