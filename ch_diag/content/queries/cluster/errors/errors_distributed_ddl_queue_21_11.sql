select
	entry,
	initiator_host,
	initiator_port,
	host,
	port,
	cluster,
	status,
	query,
	query_create_time,
	exception_code,
	exception_text
from system.distributed_ddl_queue
WHERE status != 'Finished' or exception_code != 0