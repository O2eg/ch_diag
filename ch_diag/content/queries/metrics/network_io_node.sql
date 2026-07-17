SELECT
    hostName() AS host,
    sumIf(value, event = 'NetworkReceiveBytes') AS network_receive_bytes,
    sumIf(value, event = 'NetworkSendBytes') AS network_send_bytes
FROM system.events
