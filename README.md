# ch_diag
ClickHouse diagnostic tool


```
pip install clickhouse-driver

# Connect using root CA certificate
python3 ch_diag.py \
	--user=some_user \
	--database=default \
	--host=clickhouse-host.net \
	--password=12345 \
	--ca-certs=SomeRootCA.crt \
	--port=9440

# Connect using keyfile and certfile
python3 ch_diag.py \
	--user=default \
	--password=12345 \
	--port=9410 \
	--host=127.0.0.1 \
	--keyfile=node_01.key \
	--certfile=node_01.crt

# Connect using user and password
python3 ch_diag.py \
	--user=default \
	--password=12345 \
	--port=9010 \
	--host=127.0.0.1
```