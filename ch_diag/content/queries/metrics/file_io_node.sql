SELECT
    hostName() AS host,
    sumIf(value, event = 'ReadBufferFromFileDescriptorReadBytes') AS file_read_bytes,
    sumIf(value, event = 'WriteBufferFromFileDescriptorWriteBytes') AS file_write_bytes
FROM system.events
