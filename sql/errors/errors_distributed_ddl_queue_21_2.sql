select
	entry,
	port,
	cluster,
	status,
	query,
	exception_code
from system.distributed_ddl_queue
WHERE status != 'Finished' or exception_code != 0